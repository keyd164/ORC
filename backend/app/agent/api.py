import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from .. import db
from .schemas import Question
from . import workflow
from .tools import DOCS, DOCUMENTS

router = APIRouter(prefix='/api/v1/agent', tags=['本地业务分析'])


@router.get('/capabilities')
def capabilities():
    return {'modes': ['rules', 'ollama'], 'default_mode': 'rules',
            'ollama_configured': bool(os.environ.get('KTV_OLLAMA_MODEL')),
            'tools': ['summary', 'rooms', 'exceptions', 'bills', 'documents'],
            'read_only': True, 'model_status': 'not_probed',
            'note': '规则模式不调用大模型；Ollama 模式需本机已下载模型；是否可运行以实际请求为准'}


@router.post('/runs')
def create_run(payload: Question):
    return workflow.run(payload.question.strip(), payload.mode)


@router.get('/runs')
def list_runs(limit: int = Query(20, ge=1, le=100)):
    workflow.initialize()
    with db.connection() as c:
        return [dict(row) for row in c.execute('SELECT id,question,mode,status,created_at,updated_at,error_message FROM agent_runs ORDER BY created_at DESC LIMIT ?', (limit,))]


def require_run(id):
    try:
        return workflow.detail(id)
    except KeyError:
        raise HTTPException(404, '分析记录不存在')


@router.get('/runs/{id}')
def get_run(id: str):
    return require_run(id)


@router.post('/runs/{id}/retry')
def retry(id: str):
    require_run(id)
    try:
        return workflow.run('', id=id)
    except ValueError as error:
        raise HTTPException(409, str(error))


@router.get('/runs/{id}/report')
def report(id: str):
    result = require_run(id)
    if result['status'] != 'completed':
        raise HTTPException(409, '仅完成的分析可以导出报告')
    text = '# KTV 账单业务分析报告\n\n'
    text += f"问题：{result['question']}\n\n时间：{result['created_at']}\n\n模式：{result['mode']}\n\n"
    text += result['answer']+'\n\n## 数据来源\n\n'
    text += '\n'.join('- '+source['label']+(('：'+source['url']) if source.get('url') else '') for source in result['sources'])
    text += '\n\n## 执行过程\n\n'+'\n'.join(f"- {step['node']} / {step['tool'] or '—'}：{step['status']}" for step in result['steps'])
    return Response(text.encode('utf8'), media_type='text/markdown; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename=ktv-report-{id}.md'})


@router.get('/documents/{name}')
def document(name: str):
    if name not in DOCUMENTS:
        raise HTTPException(404, '规则文档不存在')
    return {'name': name, 'text': (DOCS/name).read_text(encoding='utf8')}
