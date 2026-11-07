"""Shared engine configuration and OCR output adapter for app and benchmarks."""
import json

ENGINE_OPTIONS = {
    'lang': 'ch', 'enable_mkldnn': False,
    'use_doc_orientation_classify': False, 'use_doc_unwarping': False,
    'use_textline_orientation': False,
}


def create_engine():
    from paddleocr import PaddleOCR
    return PaddleOCR(**ENGINE_OPTIONS)


def recognize(engine, path):
    raw, lines = [], []
    for result in engine.predict(str(path)):
        item = result.json
        if isinstance(item, str):
            item = json.loads(item)
        raw.append(item)
        page = item.get('res', item)
        texts, scores, boxes = page.get('rec_texts', []), page.get('rec_scores', []), page.get('rec_polys', [])
        for index, text in enumerate(texts):
            lines.append({'text': text, 'confidence': float(scores[index]) if index < len(scores) else 0,
                          'box': boxes[index] if index < len(boxes) else None})
    return raw, lines
