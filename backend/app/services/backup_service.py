import sqlite3,zipfile,json,hashlib,tempfile,shutil
from pathlib import Path
from contextlib import closing
from datetime import datetime
from ..db import DATA,LOCK

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def create():
    with LOCK:return _create()

def _create():
    with tempfile.TemporaryDirectory() as tmp:
        stage=Path(tmp)
        with closing(sqlite3.connect(DATA/'app.db')) as src,closing(sqlite3.connect(stage/'app.db')) as dst:src.backup(dst)
        files={'app.db':digest(stage/'app.db')}
        for folder in ('uploads','processed','thumbnails'):
            for p in (DATA/folder).rglob('*'):
                if p.is_file():
                    dest=stage/p.relative_to(DATA);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);files[p.relative_to(DATA).as_posix()]=digest(dest)
        manifest={'created_at':datetime.now().astimezone().isoformat(),'database':'app.db','image_count':sum(k.startswith('uploads/') for k in files),'files':files}
        (stage/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        out=DATA/'backups'/('backup_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.zip')
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
            for p in stage.rglob('*'):
                if p.is_file():z.write(p,p.relative_to(stage).as_posix())
        return out

def verify(path):
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or sum(x.file_size for x in z.infolist())>4*1024**3:raise ValueError('备份过大或重复路径')
        for name in names:
            p=Path(name)
            if p.is_absolute() or '..' in p.parts or ':' in name or '\\' in name:raise ValueError('非法备份路径')
        m=json.loads(z.read('manifest.json'))
        if set(names)!=set(m['files'])|{'manifest.json'}:raise ValueError('文件列表不一致')
        if m.get('image_count')!=sum(k.startswith('uploads/') for k in m['files']):raise ValueError('图片数量不一致')
        for name,h in m['files'].items():
            if name!='app.db' and name.split('/')[0] not in ('uploads','processed','thumbnails'):raise ValueError('非法备份文件')
            if hashlib.sha256(z.read(name)).hexdigest()!=h:raise ValueError('哈希不一致：'+name)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'app.db';p.write_bytes(z.read('app.db'))
            with closing(sqlite3.connect(p)) as c:
                if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('数据库损坏')
                for (stored,) in c.execute('SELECT stored_path FROM images'):
                    if Path(stored).as_posix() not in m['files']:raise ValueError('原图缺失')
        return m

def restore(path):
    m=verify(path)
    with tempfile.TemporaryDirectory(dir=DATA.parent) as tmp:
        stage=Path(tmp)
        with zipfile.ZipFile(path) as z:z.extractall(stage)
        safety=create()
        for folder in ('uploads','processed','thumbnails'):
            target=DATA/folder
            if target.resolve().parent != DATA.resolve() or target.name not in ("uploads","processed","thumbnails"):raise ValueError("恢复目标越界")
            if target.exists():shutil.rmtree(target)
            shutil.copytree(stage/folder,target) if (stage/folder).exists() else target.mkdir()
        shutil.copy2(stage/'app.db',DATA/'app.db')
    return safety
