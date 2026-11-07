import io,csv,json,hashlib,logging
from uuid import uuid4
from datetime import date
from contextlib import asynccontextmanager,closing
from fastapi import FastAPI,UploadFile,File,Form,HTTPException,Body,Query
from fastapi.responses import FileResponse,Response
from PIL import Image,ImageOps,UnidentifiedImageError
from openpyxl import Workbook
from .db import DATA,init,connection,row
from .services.field_extractor import FIELDS,MONEY,normalize,validate
from .services.ocr_service import submit,now,reconcile_duplicates
from .services.backup_service import create,verify
logging.basicConfig(level=logging.INFO)
@asynccontextmanager
async def lifespan(app):
    init()
    from .agent.workflow import initialize
    initialize(recover=True)
    with connection() as c:
        for r in c.execute("SELECT id FROM images WHERE status IN ('queued','processing')"):submit(r['id'])
    yield
app=FastAPI(title='KTV 账单本地工作台',version='0.3.0',lifespan=lifespan)
P='/api/v1'
IMAGE_EXTENSIONS={'JPEG':'.jpg','PNG':'.png','WEBP':'.webp'}
from .agent.api import router as agent_router
app.include_router(agent_router)
def require(c,table,id):
    r=row(c,table,id)
    if not r:raise HTTPException(404,'记录不存在')
    return r
@app.get(P+'/health')
def health():
    with connection() as c:c.execute('SELECT 1')
    return {'status':'ok','database':'ok'}
@app.get(P+'/fields')
def fields():return FIELDS
@app.post(P+'/batches')
def batch(business_date:date=Body(embed=True)):
    id=str(uuid4())
    with connection() as c:c.execute('INSERT INTO upload_batches VALUES(?,?,?,?,?)',(id,str(business_date),now(),0,'open'))
    return {'id':id,'business_date':business_date}
@app.post(P+'/uploads')
async def upload(file:UploadFile=File(),business_date:date=Form(),batch_id:str=Form()):
    content=await file.read(15*1024*1024+1)
    if len(content)>15*1024*1024:raise HTTPException(413,'图片限制 15MB')
    try:
        with Image.open(io.BytesIO(content)) as im:
            image_format=im.format
            if image_format not in IMAGE_EXTENSIONS or im.width*im.height>40_000_000:raise ValueError('仅支持 JPEG/PNG/WebP，最多四千万像素')
            im.verify()
        # JPEG verify() alone does not decode pixel data. Reject truncated images
        # before creating any files/records, rather than failing later with 500.
        with Image.open(io.BytesIO(content)) as im:
            im.load()
            thumbnail=ImageOps.exif_transpose(im).convert('RGB')
            thumbnail.thumbnail((320,480))
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError,SyntaxError) as e:raise HTTPException(400,'图片损坏或无法完整解码：'+str(e))
    sha=hashlib.sha256(content).hexdigest();id=str(uuid4());path=DATA/'uploads'/str(business_date)/(id+IMAGE_EXTENSIONS[image_format])
    with closing(thumbnail),connection() as c:
        b=require(c,'upload_batches',batch_id)
        if b['business_date']!=str(business_date):raise HTTPException(400,'批次日期不一致')
        old=c.execute('SELECT id FROM images WHERE business_date=? AND sha256=?',(str(business_date),sha)).fetchone()
        if old:return {'image_id':old['id'],'status':'duplicate','duplicate_of':old['id']}
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
        try:
            thumbnail.save(DATA/'thumbnails'/f'{id}.jpg')
            c.execute('INSERT INTO images VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(id,batch_id,str(business_date),file.filename,str(path.relative_to(DATA)),None,sha,len(content),'queued',now(),None,None))
            c.execute("UPDATE upload_batches SET total_files=total_files+1,status='processing' WHERE id=?",(batch_id,))
        except Exception:
            path.unlink(missing_ok=True);(DATA/'thumbnails'/f'{id}.jpg').unlink(missing_ok=True);raise
    submit(id)
    return {'image_id':id,'business_date':business_date,'status':'queued'}
@app.get(P+'/images')
def images(business_date:date|None=None,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=500)):
    with connection() as c:return [dict(x) for x in c.execute('SELECT i.*,b.id bill_id,b.bill_no,b.room_name,b.received_amount FROM images i LEFT JOIN bills b ON b.image_id=i.id WHERE (? IS NULL OR i.business_date=?) ORDER BY i.uploaded_at DESC LIMIT ? OFFSET ?',(str(business_date) if business_date else None, str(business_date) if business_date else None,limit,offset))]
@app.get(P+'/images/{id}')
def image(id:str):
    with connection() as c:
        result=require(c,'images',id)
        bill=c.execute('SELECT id FROM bills WHERE image_id=?',(id,)).fetchone()
        result['bill_id']=bill['id'] if bill else None
        return result
@app.get(P+'/images/{id}/file')
def image_file(id:str,thumbnail:bool=False):
    with connection() as c:r=require(c,'images',id)
    path=DATA/'thumbnails'/f'{id}.jpg' if thumbnail else DATA/r['stored_path']
    if not path.is_file():raise HTTPException(404,'图片文件不存在')
    try:
        with Image.open(path) as im:
            media_type=Image.MIME.get(im.format,'application/octet-stream')
            extension=IMAGE_EXTENSIONS.get(im.format,'.img')
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError):
        raise HTTPException(409,'图片文件无法读取，请检查原始文件或从备份恢复')
    # MIME and suggested filename come from the header, including legacy .img.
    return FileResponse(path,media_type=media_type,filename=id+extension,content_disposition_type='inline')
@app.post(P+'/images/{id}/recognize')
def recognize(id:str):
    with connection() as c:require(c,'images',id);c.execute("UPDATE images SET status='queued' WHERE id=?",(id,))
    submit(id);return {'status':'queued'}
@app.get(P+'/images/{id}/ocr-runs')
def runs(id:str):
    with connection() as c:
        require(c,'images',id)
        return [dict(r) for r in c.execute('SELECT * FROM ocr_runs WHERE image_id=? ORDER BY started_at DESC',(id,))]
def select_bills(c,start=None,end=None,room=None,bill_no=None,review_status=None,bill_status=None,min_amount=None,max_amount=None):
    sql='SELECT b.*,i.business_date FROM bills b JOIN images i ON i.id=b.image_id WHERE 1=1';args=[]
    for clause,value in [('b.bill_date>=?',start),('b.bill_date<=?',end),('b.room_name=?',room),('b.bill_no LIKE ?',f'%{bill_no}%' if bill_no else None),('b.review_status=?',review_status),('b.bill_status=?',bill_status),('b.received_amount>=?',min_amount),('b.received_amount<=?',max_amount)]:
        if value is not None:sql+=' AND '+clause;args.append(str(value) if isinstance(value,date) else value)
    return [dict(r) for r in c.execute(sql+' ORDER BY b.created_at DESC',args)]
@app.get(P+'/bills')
def bills(start:date|None=None,end:date|None=None,room:str|None=None,bill_no:str|None=None,review_status:str|None=None,bill_status:str|None=None,min_amount:int|None=None,max_amount:int|None=None):
    with connection() as c:return select_bills(c,start,end,room,bill_no,review_status,bill_status,min_amount,max_amount)
@app.get(P+'/bills/{id}')
def detail(id:str):
    with connection() as c:
        b=require(c,'bills',id);b['fields']=[dict(x) for x in c.execute('SELECT * FROM bill_field_values WHERE bill_id=?',(id,))];b['edit_logs']=[dict(x) for x in c.execute('SELECT * FROM field_edit_logs WHERE bill_id=? ORDER BY id DESC',(id,))];b['issues']=json.loads(b['issues_json']);link=c.execute('SELECT canonical_bill_id FROM duplicate_links WHERE bill_id=?',(id,)).fetchone();b['canonical_bill_id']=link['canonical_bill_id'] if link else None;return b
@app.patch(P+'/bills/{id}/fields')
def edit(id:str,payload:dict=Body()):
    values=payload.get('fields',{});reason=str(payload.get('reason','人工校正'))
    if not values or set(values)-set(FIELDS):raise HTTPException(400,'字段为空或含不可修改字段')
    try:values={k:normalize(k,v) for k,v in values.items()}
    except Exception as e:raise HTTPException(422,str(e))
    with connection() as c:
        b=require(c,'bills',id)
        for k,v in values.items():
            c.execute(f'UPDATE bills SET {k}=? WHERE id=?',(v,id))
            c.execute('INSERT INTO field_edit_logs(bill_id,field_key,old_value,new_value,edited_at,reason) VALUES(?,?,?,?,?,?)',(id,k,json.dumps(b.get(k)),json.dumps(v),now(),reason))
            c.execute("INSERT INTO bill_field_values(bill_id,field_key,corrected_value,review_status,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(bill_id,field_key) DO UPDATE SET corrected_value=excluded.corrected_value,review_status=excluded.review_status,updated_at=excluded.updated_at",(id,k,json.dumps(v),'invalid' if v is None else 'corrected',now()))
        updated=row(c,'bills',id)
        c.execute("UPDATE bills SET review_status='pending',issues_json=?,updated_at=? WHERE id=?",(json.dumps(validate(updated),ensure_ascii=False),now(),id));reconcile_duplicates(c)
    return detail(id)
@app.post(P+'/bills/{id}/review')
def review(id:str,payload:dict=Body(default={})):
    with connection() as c:
        b=require(c,'bills',id)
        missing=c.execute("SELECT field_key FROM bill_field_values WHERE bill_id=? AND review_status='pending'",(id,)).fetchall()
        if missing and not payload.get('confirm_all'):raise HTTPException(409,'请确认识别字段或明确空值')
        if validate(b) and not payload.get('acknowledge_issues'):raise HTTPException(409,'请明确确认缺失或异常字段')
        if b['duplicate_status']!='none':raise HTTPException(409,'疑似或已确认重复账单不能复核入账，请先处理重复关系')
        c.execute("UPDATE bill_field_values SET review_status='confirmed' WHERE bill_id=? AND review_status='pending'",(id,))
        c.execute("UPDATE bills SET review_status='confirmed',updated_at=? WHERE id=?",(now(),id))
        c.execute('INSERT INTO field_edit_logs(bill_id,field_key,old_value,new_value,edited_at,reason) VALUES(?,?,?,?,?,?)',(id,'review_status',json.dumps(b['review_status']),'"confirmed"',now(),str(payload)))
    return detail(id)
def official(b):return b['review_status']=='confirmed' and b['duplicate_status']=='none' and b['bill_status']=='已结'
@app.get(P+'/dashboard/summary')
def summary(business_date:date=Query(default_factory=date.today)):
    with connection() as c:
        all=select_bills(c);today=[b for b in all if b['business_date']==str(business_date)];valid=[b for b in today if official(b)];amount=sum(b['received_amount'] or 0 for b in valid)
        counts=dict(c.execute('SELECT status,COUNT(*) FROM images WHERE business_date=? GROUP BY status',(str(business_date),)).fetchall())
        return {'business_date':business_date,'total_bills':len(all),'uploaded':sum(counts.values()),'settled':len(valid),'received_amount':amount,'average_amount':round(amount/len(valid)) if valid else 0,'pending':sum(b['review_status']!='confirmed' and b['duplicate_status']!='excluded' for b in all),'failed':counts.get('failed',0),'duplicates':sum(b['duplicate_status']=='suspected' for b in all),'completed':counts.get('completed',0),'scope':'按归档日期；营业额仅含已结、已复核、非重复账单'}
@app.get(P+'/dashboard/trend')
def trend(start:date|None=None,end:date|None=None):
    with connection() as c:
        out={}
        for r in c.execute('SELECT business_date,status FROM images'):
            d=r['business_date']
            if (start and d<str(start)) or (end and d>str(end)):continue
            v=out.setdefault(d,{'date':d,'uploaded':0,'completed':0,'reviewed':0,'settled':0,'received_amount':0});v['uploaded']+=1;v['completed']+=r['status']=='completed'
        for b in select_bills(c):
            if b['business_date'] in out:
                v=out[b['business_date']];v['reviewed']+=b['review_status']=='confirmed'
                if official(b):v['settled']+=1;v['received_amount']+=b['received_amount'] or 0
        return sorted(out.values(),key=lambda x:x['date'])
@app.get(P+'/dashboard/rooms')
def rooms(start:date|None=None,end:date|None=None):
    with connection() as c:
        out={}
        for b in select_bills(c):
            if official(b) and (not start or b['business_date']>=str(start)) and (not end or b['business_date']<=str(end)):
                r=out.setdefault(b['room_name'],{'room':b['room_name'],'count':0,'received_amount':0,'duration_minutes':0});r['count']+=1;r['received_amount']+=b['received_amount'] or 0;r['duration_minutes']+=b['duration_minutes'] or 0
        return [{**r,'average_amount':round(r['received_amount']/r['count'])} for r in out.values()]
@app.get(P+'/dashboard/exceptions')
def exceptions():
    with connection() as c:return {'bills':[b for b in select_bills(c) if b['duplicate_status']!='excluded' and (b['review_status']!='confirmed' or b['duplicate_status']=='suspected' or b['issues_json']!='[]')],'images':[dict(r) for r in c.execute("SELECT * FROM images WHERE status='failed'")]}
@app.get(P+'/exports/bills')
def export(format:str='xlsx',start:date|None=None,end:date|None=None,room:str|None=None,bill_no:str|None=None,review_status:str|None=None,bill_status:str|None=None,min_amount:int|None=None,max_amount:int|None=None):
    with connection() as c:
        rows=select_bills(c,start,end,room,bill_no,review_status,bill_status,min_amount,max_amount);keys=['business_date',*FIELDS,'review_status','duplicate_status']
        def safe(v):
            if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')):return "'"+v
            return v
        values=[[safe(str(b.get(k)/100) if k in MONEY and b.get(k) is not None else b.get(k)) for k in keys] for b in rows]
        if format=='csv':
            s=io.StringIO();w=csv.writer(s);w.writerow(keys);w.writerows(values);return Response(s.getvalue().encode('utf-8-sig'),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=bills.csv','X-Record-Count':str(len(rows))})
        if format!='xlsx':raise HTTPException(400,'仅支持 csv/xlsx')
        wb=Workbook();ws=wb.active;ws.title='Bills';ws.append(keys)
        for v in values:ws.append(v)
        wb.create_sheet('BillItems').append(['第一阶段无消费项目明细'])
        log=wb.create_sheet('ReviewLog');log.append(['bill_id','field_key','old_value','new_value','edited_at','reason'])
        ids={b['id'] for b in rows}
        for r in c.execute('SELECT * FROM field_edit_logs'):
            if r['bill_id'] in ids:log.append([safe(r[k]) for k in ['bill_id','field_key','old_value','new_value','edited_at','reason']])
        meta=wb.create_sheet('Metadata');meta.append(['exported_at',now()]);meta.append(['record_count',len(rows)]);meta.append(['金额单位','元'])
        out=io.BytesIO();wb.save(out);return Response(out.getvalue(),media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':'attachment; filename=bills.xlsx'})
@app.post(P+'/backups')
def backup():
    p=create();return {'filename':p.name,'download_url':P+'/backups/'+p.name}
@app.get(P+'/backups/{filename}')
def download_backup(filename:str):
    if Path(filename).name!=filename:raise HTTPException(400)
    p=DATA/'backups'/filename
    if not p.is_file():raise HTTPException(404)
    return FileResponse(p,filename=filename)
@app.post(P+'/backups/verify')
def verify_backup(payload:dict=Body()):
    name=payload.get('filename','')
    if Path(name).name!=name:raise HTTPException(400)
    try:return verify(DATA/'backups'/name)
    except Exception as e:raise HTTPException(400,str(e))
from pathlib import Path

@app.post(P+'/bills/{id}/duplicate')
def resolve_duplicate(id:str,payload:dict=Body()):
    target=payload.get('canonical_bill_id')
    with connection() as c:
        bill=require(c,'bills',id);canonical=require(c,'bills',target)
        if id==target or not bill['bill_no'] or bill['bill_no']!=canonical['bill_no']:
            raise HTTPException(400,'仅能关联同编号的另一张账单')
        if c.execute('SELECT 1 FROM duplicate_links WHERE bill_id=? OR canonical_bill_id=?',(target,id)).fetchone():
            raise HTTPException(409,'不能形成重复关联链，请选择原始账单')
        old=bill['duplicate_status']
        c.execute('INSERT INTO duplicate_links VALUES(?,?,?) ON CONFLICT(bill_id) DO UPDATE SET canonical_bill_id=excluded.canonical_bill_id,created_at=excluded.created_at',(id,target,now()))
        reconcile_duplicates(c)
        c.execute('INSERT INTO field_edit_logs(bill_id,field_key,old_value,new_value,edited_at,reason) VALUES(?,?,?,?,?,?)',(id,'duplicate_status',json.dumps(old),json.dumps('excluded'),now(),'人工确认重复，原始账单 '+target))
    return detail(id)

@app.get(P+'/dashboard/distributions')
def distributions(start:date|None=None,end:date|None=None):
    with connection() as c:
        groups={'payment_methods':{},'room_types':{}};sample=0
        for b in select_bills(c):
            if not official(b) or (start and b['business_date']<str(start)) or (end and b['business_date']>str(end)):continue
            sample+=1
            for key,field in [('payment_methods','payment_method'),('room_types','room_type')]:
                name=b[field] or '未记录';entry=groups[key].setdefault(name,{'name':name,'count':0,'received_amount':0})
                entry['count']+=1;entry['received_amount']+=b['received_amount'] or 0
        return {**{key:list(value.values()) for key,value in groups.items()},'sample_count':sample,'scope':'按归档日期，已结、已复核、非重复账单'}

@app.delete(P+'/bills/{id}/duplicate')
def undo_duplicate(id:str):
    with connection() as c:
        require(c,'bills',id)
        link=c.execute('SELECT canonical_bill_id FROM duplicate_links WHERE bill_id=?',(id,)).fetchone()
        if not link:raise HTTPException(409,'当前记录没有已确认的重复关系')
        c.execute('DELETE FROM duplicate_links WHERE bill_id=?',(id,))
        reconcile_duplicates(c)
        c.execute('INSERT INTO field_edit_logs(bill_id,field_key,old_value,new_value,edited_at,reason) VALUES(?,?,?,?,?,?)',(id,'duplicate_status','"excluded"','"suspected"',now(),'人工撤销重复关联 '+link['canonical_bill_id']))
    return detail(id)
