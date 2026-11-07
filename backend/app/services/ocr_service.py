import json,time,threading,logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from uuid import uuid4
from PIL import Image,ImageOps,ImageEnhance
from ..db import DATA,connection,row
from .field_extractor import extract,FIELDS,validate
from .ocr_engine import create_engine,recognize
POOL=ThreadPoolExecutor(max_workers=1,thread_name_prefix='ocr')
LOCK=threading.Lock();PENDING=set();ENGINE=None
def now():return datetime.now().astimezone().isoformat()
def submit(id):
    with LOCK:
        if id in PENDING:return
        PENDING.add(id)
    POOL.submit(run,id)
def run(id):
    global ENGINE
    rid=str(uuid4());start=now();version='unavailable';raw=[]
    try:
        with connection() as c:
            image=row(c,'images',id)
            c.execute("UPDATE images SET status='processing',error_message=NULL WHERE id=?",(id,))
        target=DATA/'processed'/f'{id}.png'
        from .preprocessing import preprocess
        preprocess(DATA/image['stored_path'],target)
        from importlib.metadata import version as package_version
        version=package_version('paddleocr')
        if ENGINE is None:ENGINE=create_engine()
        raw,lines=recognize(ENGINE,target)
        values,conf=extract(lines)
        with connection() as c:
            c.execute('INSERT INTO ocr_runs VALUES(?,?,?,?,?,?,?,?,?,?)',(rid,id,'PaddleOCR',version,'\n'.join(x['text'] for x in lines),json.dumps(raw,ensure_ascii=False),'success',None,start,now()))
            b=c.execute('SELECT * FROM bills WHERE image_id=?',(id,)).fetchone();bid=b['id'] if b else str(uuid4())
            if not b:c.execute('INSERT INTO bills(id,image_id,created_at,updated_at) VALUES(?,?,?,?)',(bid,id,now(),now()))
            for k in FIELDS:
                old=c.execute('SELECT * FROM bill_field_values WHERE bill_id=? AND field_key=?',(bid,k)).fetchone()
                detected=values.get(k)
                if old:
                    c.execute('UPDATE bill_field_values SET detected_value=?,confidence=?,source_ocr_run_id=?,updated_at=? WHERE bill_id=? AND field_key=?',(json.dumps(detected),conf.get(k),rid,now(),bid,k))
                else:c.execute('INSERT INTO bill_field_values VALUES(?,?,?,?,?,?,?,?)',(bid,k,json.dumps(detected),None,conf.get(k),'pending',rid,now()))
                if not old or old['review_status']=='pending':c.execute(f'UPDATE bills SET {k}=? WHERE id=?',(detected,bid))
            b=row(c,'bills',bid)
            c.execute('UPDATE bills SET issues_json=?,updated_at=? WHERE id=?',(json.dumps(validate(b,conf),ensure_ascii=False),now(),bid))
            reconcile_duplicates(c)
            c.execute("UPDATE images SET status='completed',processed_path=? WHERE id=?",(str(target.relative_to(DATA)),id))
    except Exception as e:
        logging.exception('OCR failed %s',id)
        with connection() as c:
            c.execute('INSERT INTO ocr_runs VALUES(?,?,?,?,?,?,?,?,?,?)',(rid,id,'PaddleOCR',version,'',json.dumps(raw,ensure_ascii=False),'failed',str(e),start,now()))
            c.execute("UPDATE images SET status='failed',error_message=? WHERE id=?",(str(e),id))
    finally:
        with connection() as c:
            image=row(c,'images',id)
            if image:
                states=[r[0] for r in c.execute('SELECT status FROM images WHERE batch_id=?',(image['batch_id'],))]
                state='processing' if any(s in ('queued','processing') for s in states) else ('completed_with_errors' if 'failed' in states else 'completed')
                c.execute('UPDATE upload_batches SET status=? WHERE id=?',(state,image['batch_id']))
        with LOCK:PENDING.discard(id)
def reconcile_duplicates(c):
    c.execute("DELETE FROM duplicate_links WHERE bill_id IN (SELECT l.bill_id FROM duplicate_links l JOIN bills b ON b.id=l.bill_id JOIN bills original ON original.id=l.canonical_bill_id WHERE b.bill_no IS NULL OR b.bill_no!=original.bill_no)")
    c.execute("UPDATE bills SET duplicate_status='none'")
    c.execute("UPDATE bills SET duplicate_status='excluded' WHERE id IN (SELECT bill_id FROM duplicate_links)")
    c.execute("UPDATE bills SET duplicate_status='suspected' WHERE duplicate_status!='excluded' AND bill_no IS NOT NULL AND bill_no!='' AND bill_no IN (SELECT bill_no FROM bills WHERE duplicate_status!='excluded' AND bill_no IS NOT NULL AND bill_no!='' GROUP BY bill_no HAVING COUNT(*)>1)")
