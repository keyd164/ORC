import hashlib
import io
import pytest
from PIL import Image
from test_system import client
from app import db


def send(client, content, name):
    batch=client.post('/api/v1/batches',json={'business_date':'2026-10-27'}).json()
    return client.post('/api/v1/uploads',data={'batch_id':batch['id'],'business_date':'2026-10-27'},
                       files={'file':(name,content,'application/octet-stream')})


@pytest.mark.parametrize('format,extension,mime',[('PNG','.png','image/png'),('JPEG','.jpg','image/jpeg'),('WEBP','.webp','image/webp')])
def test_actual_format_controls_storage_and_download(client,format,extension,mime):
    output=io.BytesIO()
    Image.new('RGB',(200,300),'white').save(output,format=format)
    data=output.getvalue()
    response=send(client,data,'misleading.img')
    assert response.status_code==200
    id=response.json()['image_id']
    record=client.get('/api/v1/images/'+id).json()
    assert record['stored_path'].endswith(extension)
    assert (db.DATA/record['stored_path']).read_bytes()==data
    assert record['sha256']==hashlib.sha256(data).hexdigest()
    downloaded=client.get('/api/v1/images/'+id+'/file')
    assert downloaded.headers['content-type']==mime
    assert ('filename="'+id+extension+'"') in downloaded.headers['content-disposition']
    assert downloaded.content==data


def test_truncated_jpeg_returns_400_and_keeps_no_upload(client):
    output=io.BytesIO()
    Image.new('RGB',(200,300),'white').save(output,format='JPEG')
    broken=output.getvalue()[:-100]
    # This is exactly why verify() alone is insufficient for JPEG.
    with Image.open(io.BytesIO(broken)) as image:
        image.verify()
    response=send(client,broken,'truncated.jpg')
    assert response.status_code==400
    assert client.get('/api/v1/images').json()==[]
    assert not list((db.DATA/'uploads').rglob('*'))
    assert not list((db.DATA/'thumbnails').iterdir())


def test_legacy_img_served_as_real_png_without_renaming_original(client):
    output=io.BytesIO()
    Image.new('RGB',(200,300),'white').save(output,format='PNG')
    data=output.getvalue()
    id=send(client,data,'test.png').json()['image_id']
    record=client.get('/api/v1/images/'+id).json()
    original=db.DATA/record['stored_path']
    legacy=original.with_suffix('.img')
    original.rename(legacy)
    with db.connection() as connection:
        connection.execute('UPDATE images SET stored_path=? WHERE id=?',(str(legacy.relative_to(db.DATA)),id))
    response=client.get('/api/v1/images/'+id+'/file')
    assert response.status_code==200 and response.content==data
    assert response.headers['content-type']=='image/png'
    assert id+'.png' in response.headers['content-disposition']
    assert legacy.is_file()


def test_unreadable_stored_image_returns_clear_error(client):
    output=io.BytesIO()
    Image.new('RGB',(200,300),'white').save(output,format='PNG')
    id=send(client,output.getvalue(),'test.png').json()['image_id']
    record=client.get('/api/v1/images/'+id).json()
    (db.DATA/record['stored_path']).write_bytes(b'corrupt')
    assert client.get('/api/v1/images/'+id+'/file').status_code==409
