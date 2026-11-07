"""Local OCR benchmark. Does not import the app DB, upload or alter bills."""
import argparse
import csv
import hashlib
import json
import math
import platform
import statistics
import sys
import threading
import time
from datetime import datetime
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
from app.services.field_extractor import extract, validate
from app.services.ocr_engine import ENGINE_OPTIONS, create_engine, recognize
from app.services.ocr_metrics import normalize_labels, score_samples


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')


def positive(value):
    value = int(value)
    if not 1 <= value <= 100:
        raise argparse.ArgumentTypeError('次数必须在1–100之间')
    return value


def summarize(records):
    successful = [r for r in records if r['status'] == 'completed']
    times = sorted(r['total_seconds'] for r in successful)
    elapsed = sum(r['total_seconds'] for r in records)
    return {'attempts': len(records), 'completed': len(successful), 'failed': len(records)-len(successful),
            'completion_rate': len(successful)/len(records) if records else None,
            'mean_seconds': statistics.mean(times) if times else None,
            'median_seconds': statistics.median(times) if times else None,
            'p95_seconds_nearest_rank': times[math.ceil(.95*len(times))-1] if times else None,
            'completed_images_per_minute': len(successful)/elapsed*60 if elapsed else None}


class MemoryMonitor:
    def __init__(self):
        self.stop = threading.Event()
        self.thread = None
        self.start_rss = self.peak_rss = None

    def __enter__(self):
        try:
            import psutil
            self.process = psutil.Process()
            self.start_rss = self.peak_rss = self.process.memory_info().rss
        except ImportError:
            return self
        def sample():
            while not self.stop.wait(.05):
                self.peak_rss = max(self.peak_rss, self.process.memory_info().rss)
        self.thread = threading.Thread(target=sample, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_):
        if self.thread:
            self.peak_rss = max(self.peak_rss, self.process.memory_info().rss)
            self.stop.set()
            self.thread.join()


def main():
    parser = argparse.ArgumentParser(description='本地OCR准确率、耗时和进程内存测试，不写业务数据库')
    parser.add_argument('--input', type=Path, default=ROOT/'data/ocr-evaluation/images')
    parser.add_argument('--expected', type=Path, default=ROOT/'data/ocr-evaluation/expected.json')
    parser.add_argument('--output', type=Path, default=ROOT/'data/ocr-evaluation/results')
    parser.add_argument('--repeat', type=positive, default=1)
    parser.add_argument('--warmup', type=int, choices=(0, 1), default=1)
    parser.add_argument('--variant', choices=('processed', 'original', 'both'), default='processed')
    parser.add_argument('--init-labels', action='store_true', help='只生成当前图片的空标注结构，不运行模型、不覆盖已有答案')
    args = parser.parse_args()
    source = args.input.resolve()
    if args.output.resolve().is_relative_to(source):
        parser.error('输出目录不能位于输入图片目录内，避免下一次误把处理图当成新样本')
    files = sorted(p for p in source.rglob('*') if p.is_file() and p.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp'))
    if not files:
        parser.error('没有找到图片。请先把 JPG/PNG/WebP 放入 '+str(source))
    filenames = [p.relative_to(source).as_posix() for p in files]
    if args.init_labels:
        if args.expected.exists():
            parser.error('标注文件已存在，为保护人工答案未覆盖：'+str(args.expected))
        args.expected.parent.mkdir(parents=True, exist_ok=True)
        write_json(args.expected, {'note': '按原图人工填写字段；金额为元。空对象表示未标注，null表示确认应为空。',
                                   'samples': {name: {} for name in filenames}})
        print('Label template: '+str(args.expected))
        return 0
    try:
        labels = normalize_labels(json.loads(args.expected.read_text(encoding='utf-8-sig'))) if args.expected.is_file() else {}
    except Exception as error:
        parser.error('人工标注文件格式错误：'+str(error))
    if set(labels)-set(filenames):
        parser.error('标注文件引用了输入目录中不存在的图片，请核对文件名')
    target = args.output.resolve()/datetime.now().strftime('run_%Y%m%d_%H%M%S_%f')
    target.mkdir(parents=True)
    variants = ['original', 'processed'] if args.variant == 'both' else [args.variant]
    records, warnings = [], []
    metadata = {'python': sys.version, 'platform': platform.platform(), 'engine_options': ENGINE_OPTIONS}
    for name in ('paddleocr', 'paddlepaddle', 'opencv-python-headless', 'psutil'):
        try:
            metadata[name] = version(name)
        except PackageNotFoundError:
            metadata[name] = None
    hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in files]
    if len(set(hashes)) < len(hashes):
        warnings.append('输入包含字节完全相同的图片，不应当作独立准确率样本')
    try:
        with MemoryMonitor() as memory:
            started = time.perf_counter()
            engine = create_engine()
            model_load = time.perf_counter()-started
            from app.services.preprocessing import preprocess
            if args.warmup:
                try:
                    warm = target/'warmup.png'
                    preprocess(files[0], warm)
                    recognize(engine, warm)
                except Exception as error:
                    warnings.append('预热失败：'+str(error))
            for variant in variants:
                for index, file in enumerate(files):
                    for repeat in range(1, args.repeat+1):
                        record = {'file': filenames[index], 'sha256': hashes[index], 'variant': variant, 'repeat': repeat,
                                  'status': 'failed', 'values': {}, 'preprocess_seconds': 0, 'ocr_seconds': 0, 'extract_seconds': 0}
                        stem = f'{index+1:04}_{variant}_{repeat}'
                        started = time.perf_counter()
                        try:
                            from PIL import Image
                            with Image.open(file) as image:
                                record['width'], record['height'] = image.size
                                if image.format not in ('JPEG', 'PNG', 'WEBP') or image.width*image.height > 40_000_000 or file.stat().st_size > 15*1024*1024:
                                    raise ValueError('与上传限制一致：JPEG/PNG/WebP，最大15MB/四千万像素')
                            path = file
                            if variant == 'processed':
                                tick = time.perf_counter()
                                path = target/(stem+'.png')
                                record['preprocessing'] = preprocess(file, path)
                                record['preprocess_seconds'] = time.perf_counter()-tick
                            tick = time.perf_counter()
                            raw, lines = recognize(engine, path)
                            record['ocr_seconds'] = time.perf_counter()-tick
                            tick = time.perf_counter()
                            record['values'], record['confidence'] = extract(lines)
                            record['issues'] = validate(record['values'], record['confidence'])
                            record['extract_seconds'] = time.perf_counter()-tick
                            record['raw_text'] = '\n'.join(line['text'] for line in lines)
                            record['status'] = 'completed'
                            # Timing ends before report serialization; no original is overwritten.
                            record['total_seconds'] = time.perf_counter()-started
                            write_json(target/(stem+'.ocr.json'), raw)
                        except Exception as error:
                            record['status'] = 'failed'
                            record['error'] = str(error)
                            record.setdefault('total_seconds', time.perf_counter()-started)
                        records.append(record)
                        print(f"{record['status']}: {record['file']} / {variant} / {repeat}: {record['total_seconds']:.3f}s")
    except Exception as error:
        write_json(target/'initialization-error.json', {'error': str(error), 'environment': metadata})
        print('OCR initialization failed. Details: '+str(target/'initialization-error.json'))
        return 2
    report = {'input_directory': str(source), 'unique_images': len(set(hashes)), 'image_files': len(files),
              'repeat': args.repeat, 'warmup': args.warmup, 'model_load_seconds': model_load,
              'rss_baseline_mb': memory.start_rss/1024**2 if memory.start_rss is not None else None,
              'rss_sampled_peak_mb': memory.peak_rss/1024**2 if memory.peak_rss is not None else None,
              'memory_scope': '当前评测进程RSS，每50ms采样；不含子进程/显存，不是操作系统严格峰值',
              'timing_scope': '单线程同步图片校验+预处理+OCR+提取；不含排队、网络、数据库、结果JSON写入；预热不计入重复统计',
              'environment': metadata, 'warnings': warnings, 'variants': {}, 'records': records}
    for variant in variants:
        report['variants'][variant] = {'performance': summarize([r for r in records if r['variant'] == variant]),
                                       'accuracy': score_samples(records, labels, variant)}
    write_json(target/'report.json', report)
    write_json(target/'manual-review.json', {'note': '机器结果供对照，金额单位分；不是人工标准答案。人工标注金额用元，不能直接复制此文件作为标注。',
                                            'samples': {r['file']: r['values'] for r in records if r['variant'] == variants[-1] and r['repeat'] == 1}})
    with (target/'timings.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['file', 'variant', 'repeat', 'status', 'preprocess_seconds', 'ocr_seconds', 'extract_seconds', 'total_seconds', 'error'], extrasaction='ignore')
        writer.writeheader()
        writer.writerows(records)
    print('Report: '+str(target/'report.json'))
    if not any(labels.values()):
        print('No human labels: field accuracy is NOT measured. Add expected.json and rerun.')
    return 1 if any(r['status'] != 'completed' for r in records) else 0


if __name__ == '__main__':
    raise SystemExit(main())
