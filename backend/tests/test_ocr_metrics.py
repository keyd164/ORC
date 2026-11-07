import pytest
from app.services.ocr_metrics import normalize_labels, score_samples
from app.services.field_extractor import REQUIRED
from app.services.ocr_engine import recognize


def record(filename, values, repeat=1, status='completed'):
    return {'file': filename, 'values': values, 'variant': 'processed', 'repeat': repeat, 'status': status}


def test_labels_use_yuan_and_validate_field_names():
    labels = normalize_labels({'samples': {'a.jpg': {'received_amount': '0.29', 'room_name': ' V11 '}}})
    assert labels['a.jpg'] == {'received_amount': 29, 'room_name': 'V11'}
    with pytest.raises(ValueError):
        normalize_labels({'samples': {'a.jpg': {'unknown_field': 1}}})
    with pytest.raises(ValueError):
        normalize_labels({'samples': {'a.jpg': {'received_amount': '1.001'}}})


def test_repeats_and_unlabeled_images_do_not_inflate_accuracy():
    rows = [record('a.jpg', {'bill_no': 'A'}), record('a.jpg', {'bill_no': 'WRONG'}, repeat=2), record('b.jpg', {})]
    result = score_samples(rows, {'a.jpg': {'bill_no': 'A'}}, 'processed')
    assert result['labeled_images'] == 1 and result['labeled_fields'] == 1
    assert result['field_accuracy'] == 1
    assert result['core_exact_match_rate'] is None
    assert score_samples(rows, {}, 'processed')['field_accuracy'] is None


def test_core_denominator_and_failure_with_expected_null():
    labels = {key: None for key in REQUIRED}
    result = score_samples([record('a.jpg', {})], {'a.jpg': labels}, 'processed')
    assert result['fully_labeled_core_images'] == 1 and result['core_exact_match_rate'] == 1
    failed = score_samples([record('a.jpg', {}, status='failed')], {'a.jpg': labels}, 'processed')
    assert failed['field_accuracy'] == 0 and failed['core_exact_match_rate'] == 0


def test_adapter_retains_text_without_boxes():
    class Result:
        json = {'res': {'rec_texts': ['账单号：A'], 'rec_scores': [.9]}}
    class Engine:
        def predict(self, path):
            return [Result()]
    raw, lines = recognize(Engine(), 'ignored.jpg')
    assert raw and lines[0]['text'] == '账单号：A' and lines[0]['box'] is None
