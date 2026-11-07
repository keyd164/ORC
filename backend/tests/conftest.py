import sys
from pathlib import Path

# 保证从项目根目录执行 pytest 时也能导入 backend/app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
