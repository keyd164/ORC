"""SQLAlchemy read-only repository; cannot execute user-provided SQL."""
import sqlite3
from contextlib import contextmanager
from sqlalchemy import create_engine, MetaData, Table, select, and_, or_, func
from sqlalchemy.pool import NullPool
from .. import db


@contextmanager
def database():
    def connect():
        connection = sqlite3.connect(db.DATA/'app.db', timeout=30)
        connection.execute('PRAGMA query_only=ON')
        return connection

    engine = create_engine('sqlite://', creator=connect, poolclass=NullPool)
    try:
        with db.LOCK, engine.connect() as connection:
            metadata = MetaData()
            bills = Table('bills', metadata, autoload_with=connection)
            images = Table('images', metadata, autoload_with=connection)
            yield connection, bills, images
    finally:
        engine.dispose()


def scope_filter(b, i, scope):
    terms = [i.c.business_date >= scope.start.isoformat(), i.c.business_date <= scope.end.isoformat()]
    if scope.room:
        terms.append(b.c.room_name == scope.room)
    return and_(*terms)


def official(b):
    return and_(b.c.review_status == 'confirmed', b.c.duplicate_status == 'none', b.c.bill_status == '已结')


def source(row):
    return {'kind': 'bill', 'id': row['id'], 'label': row.get('bill_no') or row['id'],
            'url': '/api/v1/bills/'+row['id'], 'image_id': row['image_id']}


def run_query(kind, scope, amount_only=False):
    with database() as (c, b, i):
        joined = b.join(i, b.c.image_id == i.c.id)
        where = scope_filter(b, i, scope)
        if kind == 'summary':
            row = c.execute(select(func.count().label('count'), func.coalesce(func.sum(b.c.received_amount), 0).label('received_amount'))
                            .select_from(joined).where(where, official(b))).mappings().one()
            return {'count': row['count'], 'received_amount': int(row['received_amount']), 'unit': '分',
                    'scope': '归档日期；已结、已复核、无重复争议',
                    'sources': [{'kind': 'query', 'label': '相同归档日期的有效账单汇总', 'start': str(scope.start), 'end': str(scope.end)}]}
        if kind == 'rooms':
            rows = c.execute(select(b.c.room_name.label('room'), func.count().label('count'),
                                    func.coalesce(func.sum(b.c.received_amount), 0).label('received_amount'))
                             .select_from(joined).where(where, official(b)).group_by(b.c.room_name)
                             .order_by(func.sum(b.c.received_amount).desc(), b.c.room_name).limit(20)).mappings().all()
            return {'rows': [dict(r) for r in rows], 'limit': 20, 'scope': '有效账单房间排行，实收单位分',
                    'sources': [{'kind': 'query', 'label': '房间排行 SQL 聚合', 'start': str(scope.start), 'end': str(scope.end)}]}
        if kind in ('exceptions', 'bills'):
            if kind == 'exceptions':
                where = and_(where, b.c.duplicate_status != 'excluded',
                             or_(b.c.review_status != 'confirmed', b.c.duplicate_status == 'suspected', b.c.issues_json != '[]'))
                if amount_only:
                    where = and_(where, or_(b.c.received_amount < 0, b.c.receivable_amount < 0,
                                          b.c.total_amount < 0, b.c.received_amount != b.c.receivable_amount,
                                          b.c.issues_json.contains('金额'), b.c.issues_json.contains('_amount')))
            columns = [b.c.id, b.c.image_id, b.c.bill_no, b.c.room_name, b.c.received_amount,
                       b.c.review_status, b.c.duplicate_status, b.c.issues_json, i.c.business_date]
            total = c.scalar(select(func.count()).select_from(joined).where(where))
            rows = c.execute(select(*columns).select_from(joined).where(where)
                             .order_by(i.c.business_date.desc(), b.c.id).limit(50)).mappings().all()
            result = {'rows': [dict(r) for r in rows], 'total': total, 'limit': 50,
                      'sources': [source(dict(r)) for r in rows]}
            if kind == 'exceptions':
                image_where = and_(i.c.business_date >= str(scope.start), i.c.business_date <= str(scope.end), i.c.status == 'failed')
                failed = [] if scope.room or amount_only else c.execute(select(i.c.id, i.c.original_name, i.c.error_message)
                                                         .where(image_where).order_by(i.c.id).limit(20)).mappings().all()
                result['failed_images'] = [dict(row) for row in failed]
                result['failed_image_count'] = 0 if scope.room or amount_only else c.scalar(select(func.count()).select_from(i).where(image_where))
                result['exception_scope'] = '金额异常' if amount_only else '异常与待复核'
                result['sources'].extend({'kind': 'image', 'id': row['id'], 'label': row['original_name'],
                                          'url': '/api/v1/images/'+row['id']} for row in failed)
                if scope.room:
                    result['note'] = 'OCR 失败图片房间未知，不加入指定房间查询'
            return result
        raise ValueError('不允许的查询工具')
