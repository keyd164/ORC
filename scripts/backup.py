import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.db import init
from app.services.backup_service import create,verify
init();path=create();verify(path);print(path)
