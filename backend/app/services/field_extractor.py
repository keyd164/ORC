import json,re,os
from pathlib import Path
from decimal import Decimal,InvalidOperation
from datetime import datetime,date
FIELDS=json.loads((Path(__file__).resolve().parents[2]/'config/bill_fields.json').read_text(encoding='utf-8'))
MONEY={k for k in FIELDS if k.endswith('_amount')}
REQUIRED={'bill_no','bill_date','room_name','open_time','close_time','duration_minutes','total_amount','receivable_amount','received_amount','bill_status'}
def normalize(k,v):
    if v is None or v=='': return None
    if k in MONEY:
        n=Decimal(str(v).replace('元','').replace('¥','').replace('￥','').replace(',','').strip())*100
        if not n.is_finite() or n!=n.to_integral_value(): raise ValueError('金额最多两位小数')
        return int(n)
    if k in ('duration_minutes','print_count'):
        return int(str(v).replace('分钟','').replace('次','').strip())
    if k.endswith('_time'): return datetime.fromisoformat(str(v).strip()).isoformat(sep=' ')
    if k=='bill_date': return date.fromisoformat(str(v).strip()).isoformat()
    return str(v).strip()
def extract(lines):
    values={};confidence={}
    for i,line in enumerate(lines):
        text=line['text']
        for k,labels in FIELDS.items():
            m=re.search(r'(?:'+labels+r')\s*[:：]?\s*(.*)',text)
            if m:
                candidate=m[1].strip()
                if not candidate and i+1<len(lines): candidate=lines[i+1]['text'].strip()
                try: values[k]=normalize(k,candidate);confidence[k]=min(line.get('confidence',0),lines[i+1].get('confidence',0)) if not m[1].strip() and i+1<len(lines) else line.get('confidence',0)
                except (ValueError,InvalidOperation): pass
    return values,confidence
def validate(v,confidence=None,threshold=None):
    threshold=int(os.environ.get("KTV_DURATION_TOLERANCE_MINUTES","15")) if threshold is None else threshold
    errors=[f'缺失字段：{k}' for k in REQUIRED if v.get(k) is None]
    for k in MONEY:
        if v.get(k) is not None and v[k]<0: errors.append(f'负数金额：{k}')
    if v.get('received_amount')!=v.get('receivable_amount'):errors.append('实收与应收不一致')
    if v.get('open_time') and v.get('close_time'):
        delta=(datetime.fromisoformat(v['close_time'])-datetime.fromisoformat(v['open_time'])).total_seconds()/60
        if delta<0: errors.append('关房早于开房')
        if v.get('duration_minutes') is not None and abs(delta-v['duration_minutes'])>threshold: errors.append('消费时长与开关房时间不一致')
    for k,c in (confidence or {}).items():
        if k in REQUIRED and c<0.85:errors.append(f'低置信度：{k}')
    return errors
