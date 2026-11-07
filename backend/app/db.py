import sqlite3,os,json
from pathlib import Path
from contextlib import contextmanager
from threading import RLock
LOCK=RLock()
from .services.field_extractor import FIELDS,MONEY
DATA=Path(os.environ.get('KTV_DATA_DIR',Path(__file__).resolve().parents[2]/'data')).resolve()
def init():
    for name in ('uploads','processed','thumbnails','exports','backups'): (DATA/name).mkdir(parents=True,exist_ok=True)
    with connection() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS upload_batches(id TEXT PRIMARY KEY,business_date TEXT,uploaded_at TEXT,total_files INTEGER DEFAULT 0,status TEXT);
        CREATE TABLE IF NOT EXISTS images(id TEXT PRIMARY KEY,batch_id TEXT,business_date TEXT,original_name TEXT,stored_path TEXT,processed_path TEXT,sha256 TEXT,size_bytes INTEGER,status TEXT,uploaded_at TEXT,duplicate_of TEXT,error_message TEXT);
        CREATE TABLE IF NOT EXISTS ocr_runs(id TEXT PRIMARY KEY,image_id TEXT,engine TEXT,engine_version TEXT,raw_text TEXT,result_json TEXT,status TEXT,error_message TEXT,started_at TEXT,completed_at TEXT);
        CREATE TABLE IF NOT EXISTS bills(id TEXT PRIMARY KEY,image_id TEXT UNIQUE,review_status TEXT DEFAULT 'pending',duplicate_status TEXT DEFAULT 'none',issues_json TEXT DEFAULT '[]',created_at TEXT,updated_at TEXT);
        CREATE TABLE IF NOT EXISTS bill_field_values(bill_id TEXT,field_key TEXT,detected_value TEXT,corrected_value TEXT,confidence REAL,review_status TEXT,source_ocr_run_id TEXT,updated_at TEXT,PRIMARY KEY(bill_id,field_key));
        CREATE TABLE IF NOT EXISTS duplicate_links(bill_id TEXT PRIMARY KEY,canonical_bill_id TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS field_edit_logs(id INTEGER PRIMARY KEY AUTOINCREMENT,bill_id TEXT,field_key TEXT,old_value TEXT,new_value TEXT,edited_at TEXT,reason TEXT);
        CREATE INDEX IF NOT EXISTS images_hash ON images(sha256,business_date);
        CREATE INDEX IF NOT EXISTS images_date ON images(business_date);
        CREATE INDEX IF NOT EXISTS images_status ON images(status);
        CREATE INDEX IF NOT EXISTS runs_image ON ocr_runs(image_id);
        """)
        cols={r[1] for r in c.execute('PRAGMA table_info(bills)')}
        for k in FIELDS:
            if k not in cols:c.execute(f'ALTER TABLE bills ADD COLUMN {k} '+('INTEGER' if k in MONEY or k in ('duration_minutes','print_count') else 'TEXT'))
        for k in ('bill_no','bill_date','room_name','review_status'):c.execute(f'CREATE INDEX IF NOT EXISTS bills_{k} ON bills({k})')
@contextmanager
def connection():
    with LOCK:
        c=sqlite3.connect(DATA/'app.db',timeout=30);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
        try:
            yield c;c.commit()
        except Exception:
            c.rollback();raise
        finally:c.close()

def row(c,table,id):
    r=c.execute(f'SELECT * FROM {table} WHERE id=?',(id,)).fetchone()
    return dict(r) if r else None
