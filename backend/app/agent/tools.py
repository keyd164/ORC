import re
from pathlib import Path
from langchain_core.tools import tool
from .schemas import Scope
from .repository import run_query

DOCS = Path(__file__).resolve().parents[3]/'docs'
DOCUMENTS = ('business-rules.md',)


def search_docs(question):
    tokens = set(re.findall(r'[a-zA-Z_]+|[\u4e00-\u9fff]{2}', question))
    hits = []
    for name in DOCUMENTS:
        path = DOCS/name
        if not path.is_file():
            continue
        for number, paragraph in enumerate(path.read_text(encoding='utf8').split('\n\n'), 1):
            score = sum(token.lower() in paragraph.lower() for token in tokens)
            if score:
                hits.append({'score': score, 'text': paragraph[:1200], 'file': name, 'section': number})
    hits = sorted(hits, key=lambda hit: -hit['score'])[:4]
    return {'passages': hits, 'retrieval': '本地关键词检索，非向量语义检索',
            'sources': [{'kind': 'document', 'label': hit['file']+' 第'+str(hit['section'])+'段',
                         'url': '/api/v1/agent/documents/'+hit['file']} for hit in hits]}


@tool
def business_query(kind: str, start: str, end: str, room: str | None = None, question: str = '') -> dict:
    """Read-only KTV tools: summary, rooms, exceptions, bills, documents. Money is integer cents."""
    scope = Scope(start=start, end=end, room=room)
    return search_docs(question) if kind == 'documents' else run_query(kind, scope, amount_only='金额异常' in question)
