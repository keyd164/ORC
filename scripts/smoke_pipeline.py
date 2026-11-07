"""Real local OCR integration smoke test, using isolated temporary data."""
import io
import os
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='ktv-pipeline-') as temporary:
        os.environ['KTV_DATA_DIR'] = temporary
        sys.path.insert(0, str(root / 'backend'))
        from fastapi.testclient import TestClient
        from app.main import app
        from app.services.ocr_service import POOL

        image = Image.new('RGB', (900, 1400), 'white')
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 32)
        lines = [
            '本地合成测试票据', '账单号：R26102500003', '账单日期：2026-10-25',
            '房间名称：V11', '开房时间：2026-10-25 10:00:00',
            '关房时间：2026-10-25 14:00:00', '消费时长：240分钟',
            '消费合计：80.00', '应收金额：80.00', '实收金额：80.00', '结算状态：已结',
        ]
        for index, text in enumerate(lines):
            draw.text((45, 50 + index * 105), text, font=font, fill='black')
        content = io.BytesIO()
        image.save(content, format='PNG')

        try:
            with TestClient(app) as client:
                batch = client.post('/api/v1/batches', json={'business_date': '2026-10-25'}).json()
                form = {'business_date': '2026-10-25', 'batch_id': batch['id']}
                files = {'file': ('synthetic.png', content.getvalue(), 'image/png')}
                response = client.post('/api/v1/uploads', data=form, files=files)
                assert response.status_code == 200, response.text
                image_id = response.json()['image_id']
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    result = client.get('/api/v1/images/' + image_id).json()
                    if result['status'] in ('completed', 'failed'):
                        break
                    time.sleep(.5)
                assert result['status'] == 'completed', result
                bill_id = result['bill_id']
                bill = client.get('/api/v1/bills/' + bill_id).json()
                assert bill['bill_no'] == 'R26102500003', bill
                assert bill['room_name'] == 'V11', bill
                assert bill['received_amount'] == 8000, bill
                duplicate = client.post('/api/v1/uploads', data=form, files=files)
                assert duplicate.json()['status'] == 'duplicate', duplicate.text
                summary_path = '/api/v1/dashboard/summary?business_date=2026-10-25'
                assert client.get(summary_path).json()['received_amount'] == 0
                reviewed = client.post('/api/v1/bills/' + bill_id + '/review', json={
                    'confirm_all': True, 'acknowledge_issues': True,
                })
                assert reviewed.status_code == 200, reviewed.text
                assert client.get(summary_path).json()['received_amount'] == 8000
                assert client.get('/api/v1/exports/bills?format=csv').content.startswith(b'\xef\xbb\xbf')
                assert client.get('/api/v1/exports/bills?format=xlsx').content.startswith(b'PK')
                backup = client.post('/api/v1/backups').json()
                verified = client.post('/api/v1/backups/verify', json={'filename': backup['filename']})
                assert verified.status_code == 200, verified.text
                assert verified.json()['image_count'] == 1
                print('PASS: upload -> real local OCR -> review -> revenue -> CSV/XLSX -> verified backup')
        finally:
            POOL.shutdown(wait=True)


if __name__ == '__main__':
    main()
