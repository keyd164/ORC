import io,json,sys,zipfile
from pathlib import Path
from uuid import uuid4
import pytest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import db
from app.main import app
from app.services import ocr_service,backup_service
from app.services.field_extractor import normalize,extract,validate
from fastapi.testclient import TestClient
@pytest.fixture
def client(tmp_path,monkeypatch):
    for module in (db,sys.modules['app.main'],ocr_service,backup_service):monkeypatch.setattr(module,'DATA',tmp_path)
    monkeypatch.setattr(sys.modules['app.main'],'submit',lambda _:None)
    with TestClient(app) as client:yield client

def image():
    buf=io.BytesIO();Image.new('RGB',(200,300),'white').save(buf,format='PNG');return buf.getvalue()
def upload(client):
    b=client.post('/api/v1/batches',json={'business_date':'2026-10-25'}).json()
    return client.post('/api/v1/uploads',data={'batch_id':b['id'],'business_date':'2026-10-25'},files={'file':('receipt.png',image(),'image/png')})
def seed(client,no='R26102500003'):
    im=upload(client).json()['image_id'];bid=str(uuid4())
    with db.connection() as c:
        c.execute("INSERT INTO bills(id,image_id,bill_no,bill_date,room_name,open_time,close_time,duration_minutes,total_amount,receivable_amount,received_amount,bill_status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(bid,im,no,'2026-10-25','V11','2026-10-25 10:00:00','2026-10-25 14:00:00',240,8000,8000,8000,'已结','now','now'))
    return bid

def test_health_and_duplicate(client):
    assert client.get('/api/v1/health').status_code==200
    a=upload(client);assert a.status_code==200
    b=upload(client);assert b.json()['status']=='duplicate'
    assert len(client.get('/api/v1/images').json())==1

def test_invalid_upload(client):
    b=client.post('/api/v1/batches',json={'business_date':'2026-10-25'}).json()
    r=client.post('/api/v1/uploads',data={'batch_id':b['id'],'business_date':'2026-10-25'},files={'file':('x.png',b'not an image','image/png')})
    assert r.status_code==400

def test_money_and_extract():
    assert normalize('received_amount','80.01')==8001
    with pytest.raises(Exception):normalize('received_amount','1.001')
    values,conf=extract([{'text':'账单号：R26102500003','confidence':.99},{'text':'实收金额：80.00','confidence':.95}])
    assert values['received_amount']==8000
    assert values['bill_no']=='R26102500003'
    assert validate(values)

def test_review_null_and_statistics(client):
    bid=seed(client)
    assert client.get('/api/v1/dashboard/summary?business_date=2026-10-25').json()['received_amount']==0
    assert client.post(f'/api/v1/bills/{bid}/review',json={'confirm_all':True}).status_code==200
    assert client.get('/api/v1/dashboard/summary?business_date=2026-10-25').json()['received_amount']==8000
    assert client.patch(f'/api/v1/bills/{bid}/fields',json={'fields':{'received_amount':None}}).status_code==200
    b=client.get(f'/api/v1/bills/{bid}').json();assert b['received_amount'] is None
    assert b['fields'][0]['corrected_value']=='null'
    assert len(b['edit_logs'])==2
    assert client.post(f'/api/v1/bills/{bid}/review',json={}).status_code==409
    assert client.post(f'/api/v1/bills/{bid}/review',json={'acknowledge_issues':True}).status_code==200

def test_protected_fields(client):
    bid=seed(client)
    assert client.patch(f'/api/v1/bills/{bid}/fields',json={'fields':{'review_status':'confirmed'}}).status_code==400

def test_backup_and_export(client):
    seed(client)
    csv=client.get('/api/v1/exports/bills?format=csv');assert csv.content.startswith(b'\xef\xbb\xbf')
    assert b'80.0' in csv.content
    x=client.get('/api/v1/exports/bills?format=xlsx');assert zipfile.is_zipfile(io.BytesIO(x.content))
    b=client.post('/api/v1/backups').json();r=client.post('/api/v1/backups/verify',json={'filename':b['filename']});assert r.status_code==200;assert r.json()['image_count']==1
    archive=db.DATA/'backups'/b['filename'];safety=backup_service.restore(archive);assert safety.exists()
    assert len(client.get('/api/v1/images').json())==1

def test_duplicate_bill_excluded(client):
    bid=seed(client)
    with db.connection() as c:
        c.execute("INSERT INTO bills(id,image_id,bill_no,review_status,bill_status,received_amount) VALUES(?,?,?,?,?,?)",('second','different-image','R26102500003','confirmed','已结',8000))
        ocr_service.reconcile_duplicates(c)
    assert client.post(f'/api/v1/bills/{bid}/review',json={'confirm_all':True}).status_code==409
    assert client.get('/api/v1/dashboard/summary?business_date=2026-10-25').json()['received_amount']==0

def test_zip_traversal(client,tmp_path):
    path=tmp_path/'bad.zip'
    with zipfile.ZipFile(path,'w') as z:z.writestr('../escape','oops')
    with pytest.raises(ValueError):backup_service.verify(path)

def test_ocr_rerun_preserves_corrections(client,monkeypatch):
    import types
    import importlib.metadata
    original_version=importlib.metadata.version
    monkeypatch.setattr(importlib.metadata,'version',lambda name:'test-version' if name=='paddleocr' else original_version(name))
    bid=seed(client)
    client.patch(f'/api/v1/bills/{bid}/fields',json={'fields':{'room_name':'V99','cashier':None}})
    class Result:
        json={'res':{'rec_texts':['房间名称：V11','实收金额：80.00'],'rec_scores':[.99,.99],'rec_polys':[[[0,0],[100,0],[100,20],[0,20]],[[0,30],[100,30],[100,50],[0,50]]]}}
    class Engine:
        def predict(self,path):return [Result()]
    monkeypatch.setitem(sys.modules,'paddleocr',types.SimpleNamespace(PaddleOCR=lambda **_:Engine()))
    monkeypatch.setattr(ocr_service,'ENGINE',None)
    # Preprocessing is tested separately; isolate this persistence test from native engines.
    monkeypatch.setitem(sys.modules,'app.services.preprocessing',types.SimpleNamespace(preprocess=lambda source,target:target.write_bytes(source.read_bytes())))
    im=client.get(f'/api/v1/bills/{bid}').json()['image_id']
    ocr_service.run(im);ocr_service.run(im)
    b=client.get(f'/api/v1/bills/{bid}').json()
    assert b['room_name']=='V99' and b['cashier'] is None
    assert len(client.get(f'/api/v1/images/{im}/ocr-runs').json())==2
    field=next(f for f in b['fields'] if f['field_key']=='room_name')
    assert json.loads(field['detected_value'])=='V11'
    assert json.loads(field['corrected_value'])=='V99'

def test_ocr_failure_keeps_original(client,monkeypatch):
    import types
    im=upload(client).json()['image_id']
    monkeypatch.setitem(sys.modules,'app.services.preprocessing',types.SimpleNamespace(preprocess=lambda *_: (_ for _ in ()).throw(RuntimeError('deliberate failure'))))
    ocr_service.run(im)
    r=client.get(f'/api/v1/images/{im}').json()
    assert r['status']=='failed'
    assert client.get(f'/api/v1/images/{im}/file').status_code==200
    assert client.get(f'/api/v1/images/{im}/ocr-runs').json()[0]['status']=='failed'

def test_image_lookup_pagination_and_mime(client):
    bid=seed(client)
    rows=client.get('/api/v1/images?limit=1&offset=0').json()
    assert len(rows)==1
    assert client.get('/api/v1/images?limit=1&offset=1').json()==[]
    assert client.get('/api/v1/images?offset=-1').status_code==422
    assert client.get('/api/v1/images/'+rows[0]['id']).json()['bill_id']==bid
    assert client.get('/api/v1/images/'+rows[0]['id']+'/file').headers['content-type']=='image/png'

def test_resolve_duplicates_counts_only_canonical(client):
    bid=seed(client)
    with db.connection() as c:
        original=c.execute('SELECT image_id FROM bills WHERE id=?',(bid,)).fetchone()[0]
        c.execute("INSERT INTO images SELECT 'second-image',batch_id,business_date,original_name,stored_path,processed_path,'new-hash',size_bytes,status,uploaded_at,duplicate_of,error_message FROM images WHERE id=?",(original,))
        c.execute("INSERT INTO bills(id,image_id,bill_no,review_status,bill_status,received_amount,room_name) VALUES(?,?,?,?,?,?,?)",('second','second-image','R26102500003','confirmed','已结',8000,'V11'))
        ocr_service.reconcile_duplicates(c)
    assert client.post(f'/api/v1/bills/{bid}/duplicate',json={'canonical_bill_id':bid}).status_code==400
    assert client.post('/api/v1/bills/second/duplicate',json={'canonical_bill_id':bid}).status_code==200
    assert client.get('/api/v1/bills/second').json()['duplicate_status']=='excluded'
    assert client.get('/api/v1/bills/second').json()['canonical_bill_id']==bid
    assert client.get(f'/api/v1/bills/{bid}').json()['duplicate_status']=='none'
    assert client.post(f'/api/v1/bills/{bid}/review',json={'confirm_all':True}).status_code==200
    assert client.get('/api/v1/dashboard/summary?business_date=2026-10-25').json()['received_amount']==8000
    assert client.get('/api/v1/dashboard/distributions').json()['sample_count']==1
    assert client.post(f'/api/v1/bills/{bid}/duplicate',json={'canonical_bill_id':'second'}).status_code==409
    # A corrected OCR number must invalidate the stale duplicate link.
    client.patch('/api/v1/bills/second/fields',json={'fields':{'bill_no':'R26102500099'}})
    assert client.get('/api/v1/bills/second').json()['duplicate_status']=='none'

def test_distributions_and_rooms_share_date_scope(client):
    bid=seed(client)
    client.patch(f'/api/v1/bills/{bid}/fields',json={'fields':{'payment_method':'微信','room_type':'中包'}})
    client.post(f'/api/v1/bills/{bid}/review',json={'confirm_all':True})
    d=client.get('/api/v1/dashboard/distributions?start=2026-10-25&end=2026-10-25').json()
    assert d['payment_methods']==[{'name':'微信','count':1,'received_amount':8000}]
    assert d['room_types'][0]['name']=='中包'
    assert client.get('/api/v1/dashboard/distributions?start=2026-10-26').json()['sample_count']==0
    r=client.get('/api/v1/dashboard/rooms?end=2026-10-25').json()[0]
    assert r['average_amount']==8000 and r['duration_minutes']==240
    assert client.get('/api/v1/dashboard/rooms?start=2026-10-26').json()==[]

def test_revoke_duplicate_reopens_dispute(client):
    bid=seed(client)
    with db.connection() as c:
        c.execute("INSERT INTO bills(id,image_id,bill_no,review_status,bill_status,received_amount) VALUES(?,?,?,?,?,?)",('second','different-image','R26102500003','pending','已结',8000))
        ocr_service.reconcile_duplicates(c)
    client.post('/api/v1/bills/second/duplicate',json={'canonical_bill_id':bid})
    client.post(f'/api/v1/bills/{bid}/review',json={'confirm_all':True})
    summary=client.get('/api/v1/dashboard/summary?business_date=2026-10-25').json()
    assert summary['duplicates']==0 and summary['pending']==0
    assert client.get('/api/v1/dashboard/exceptions').json()['bills']==[]
    assert client.delete('/api/v1/bills/second/duplicate').status_code==200
    assert client.get(f'/api/v1/bills/{bid}').json()['duplicate_status']=='suspected'
    assert client.get('/api/v1/dashboard/summary?business_date=2026-10-25').json()['received_amount']==0
    assert client.delete('/api/v1/bills/second/duplicate').status_code==409
