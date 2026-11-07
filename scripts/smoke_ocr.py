from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
p=Path('data/ocr-smoke');p.mkdir(parents=True,exist_ok=True)
im=Image.new('RGB',(900,1400),'white');d=ImageDraw.Draw(im);f=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',32)
for i,t in enumerate(['本地合成测试票据','账单号：R26102500003','账单日期：2026-10-25','房间名称：V11','开房时间：2026-10-25 10:00:00','关房时间：2026-10-25 14:00:00','消费时长：240分钟','消费合计：80.00','应收金额：80.00','实收金额：80.00','结算状态：已结']):d.text((45,50+i*105),t,font=f,fill='black')
im.save(p/'synthetic.png')
from paddleocr import PaddleOCR
import json
ocr=PaddleOCR(lang='ch',enable_mkldnn=False,use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False)
results=[]
for r in ocr.predict(str(p/'synthetic.png')):
 item=r.json
 if isinstance(item,str):item=json.loads(item)
 results.append(item)
(p/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
print('OCR smoke completed; results saved locally')
