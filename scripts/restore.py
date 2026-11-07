import sys,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.services.backup_service import restore,verify
p=argparse.ArgumentParser(description='先关闭后端，再校验恢复。原数据自动备份。');p.add_argument('archive',type=Path);p.add_argument('--apply',action='store_true');a=p.parse_args()
m=verify(a.archive);print('校验通过，原图数量：',m['image_count'])
if a.apply:print('已恢复，恢复前备份：',restore(a.archive))
else:print('仅校验；实际恢复请加 --apply')
