"""Ground-truth comparison. Repeated speed runs never inflate sample counts."""
from .field_extractor import FIELDS, REQUIRED, normalize


def normalize_labels(document):
    samples = document.get('samples', {})
    if not isinstance(samples, dict):
        raise ValueError('expected.json 的 samples 必须为对象')
    normalized = {}
    for filename, fields in samples.items():
        if not isinstance(fields, dict) or set(fields)-set(FIELDS):
            raise ValueError(f'{filename} 包含未知字段，或字段答案不是对象')
        normalized[filename] = {key: normalize(key, value) for key, value in fields.items()}
    return normalized


def score_samples(records, labels, variant):
    # Accuracy is measured once per image, including first-attempt failures.
    rows = [r for r in records if r['variant'] == variant and r['repeat'] == 1]
    totals, comparisons = {}, []
    full_count = full_correct = labeled_images = 0
    for row in rows:
        expected = labels.get(row['file'], {})
        if not expected:
            continue
        labeled_images += 1
        matches = {}
        for field, answer in expected.items():
            detected = row.get('values', {}).get(field)
            correct = row['status'] == 'completed' and detected == answer
            matches[field] = correct
            counter = totals.setdefault(field, {'correct': 0, 'labeled': 0})
            counter['labeled'] += 1
            counter['correct'] += int(correct)
            comparisons.append({'file': row['file'], 'field': field, 'expected': answer,
                                'detected': detected, 'correct': correct})
        if REQUIRED.issubset(expected):
            full_count += 1
            full_correct += int(all(matches[field] for field in REQUIRED))
    correct = sum(r['correct'] for r in totals.values())
    count = sum(r['labeled'] for r in totals.values())
    return {'labeled_images': labeled_images, 'correct_fields': correct, 'labeled_fields': count,
            'field_accuracy': correct/count if count else None,
            'per_field': {key: {**value, 'accuracy': value['correct']/value['labeled']} for key, value in totals.items()},
            'fully_labeled_core_images': full_count, 'core_exact_matches': full_correct,
            'core_exact_match_rate': full_correct/full_count if full_count else None,
            'comparisons': comparisons}
