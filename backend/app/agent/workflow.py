import json
import os
import re
import time
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import TypedDict
from uuid import uuid4
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
from langgraph.graph import StateGraph, START, END
from .. import db
from .schemas import Plan, Scope
from .tools import business_query


class State(TypedDict, total=False):
    id: str
    question: str
    mode: str
    plan: dict
    next_tool: int
    results: list
    answer: str
    error: str


WRITE_WORDS = ('删除', '修改', '改成', '更新账单', '执行sql', 'drop table', 'delete from', 'update bills', '上传外部', '忽略规则')


def now():
    return datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()


def initialize(recover=False):
    with db.connection() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS agent_runs(id TEXT PRIMARY KEY,question TEXT NOT NULL,mode TEXT NOT NULL,status TEXT NOT NULL,state_json TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,error_message TEXT);
        CREATE TABLE IF NOT EXISTS agent_steps(id INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT NOT NULL,node TEXT NOT NULL,tool TEXT,args_json TEXT,result_json TEXT,status TEXT NOT NULL,error_message TEXT,elapsed_ms INTEGER,created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS agent_steps_run ON agent_steps(run_id,id);
        ''')
        if recover:
            c.execute("UPDATE agent_runs SET status='interrupted',updated_at=? WHERE status='running'", (now(),))


def save(state, status='running'):
    with db.connection() as c:
        c.execute('UPDATE agent_runs SET state_json=?,status=?,updated_at=?,error_message=? WHERE id=?',
                  (json.dumps(state, ensure_ascii=False), status, now(), state.get('error'), state['id']))


def log(id, node, tool=None, args=None, result=None, status='success', error=None, elapsed=0):
    with db.connection() as c:
        c.execute('INSERT INTO agent_steps(run_id,node,tool,args_json,result_json,status,error_message,elapsed_ms,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
                  (id, node, tool, json.dumps(args, ensure_ascii=False), json.dumps(result, ensure_ascii=False), status, error, elapsed, now()))


def rule_plan(question, today=None):
    today = today or datetime.now(ZoneInfo('Asia/Shanghai')).date()
    if any(word in question.lower() for word in WRITE_WORDS):
        raise ValueError('业务分析工具仅支持只读查询，修改和删除请进入账单页面人工操作')
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', question)
    if len(dates) > 2:
        raise ValueError('单次问题请最多指定一个日期范围')
    if dates:
        start = date.fromisoformat(dates[0])
        end = date.fromisoformat(dates[1]) if len(dates) > 1 else start
    elif '本月' in question:
        start, end = today.replace(day=1), today
    elif '上月' in question:
        end = today.replace(day=1)-timedelta(days=1)
        start = end.replace(day=1)
    elif '昨天' in question:
        start = end = today-timedelta(days=1)
    elif '前天' in question:
        start = end = today-timedelta(days=2)
    elif '本周' in question:
        start, end = today-timedelta(days=today.weekday()), today
    elif '上周' in question:
        end = today-timedelta(days=today.weekday()+1)
        start = end-timedelta(days=6)
    elif '今年' in question:
        start, end = today.replace(month=1, day=1), today
    elif re.search(r'近(\d+)天', question):
        days = int(re.search(r'近(\d+)天', question)[1])
        if not 1 <= days <= 3660:
            raise ValueError('最近天数必须在 1–3660 之间')
        start, end = today-timedelta(days=days-1), today
    elif '近七天' in question:
        start, end = today-timedelta(days=6), today
    else:
        if any(word in question for word in ('全部', '所有', '累计', '去年', '月', '年')):
            raise ValueError('请明确日期范围，例如 2026-10-01 至 2026-10-26')
        start = end = today
    match = re.search(r'\b[Vv]\d{1,4}\b', question)
    tools = []
    if any(w in question for w in ('最高', '排行', '排名', '房间统计')):
        tools.append('rooms')
    if any(w in question for w in ('异常', '待复核', '重复', '失败')):
        tools.append('exceptions')
    if any(w in question for w in ('口径', '规则', '为什么', '如何', '怎么', '是什么')):
        tools.append('documents')
    if any(w in question for w in ('合计', '总额', '收入', '实收', '汇总', '报告')):
        tools.append('summary')
    if any(w in question for w in ('明细', '查询账单', '列出账单')) or ('账单' in question and any(w in question for w in ('查询', '列出', '查看'))):
        tools.append('bills')
    if not tools:
        raise ValueError('规则模式支持：日期实收汇总、房间排行、异常账单、账单明细和业务规则；请明确查询内容')
    return Plan(scope=Scope(start=start, end=end, room=match[0].upper() if match else None), tools=list(dict.fromkeys(tools)))


def ollama_plan(question):
    from langchain_ollama import ChatOllama
    from urllib.request import build_opener, ProxyHandler, Request
    url = os.environ.get('KTV_OLLAMA_URL', 'http://127.0.0.1:11434')
    parsed = urlparse(url)
    if (parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1')
            or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise ValueError('模型地址只允许本机 HTTP Ollama，不允许外部服务')
    model = os.environ.get('KTV_OLLAMA_MODEL', '').strip()
    if not model or any(word in model.lower() for word in ('cloud', ':remote')):
        raise ValueError('请配置已在本机下载的 Ollama 模型；不允许云模型')
    opener = build_opener(ProxyHandler({}))
    with opener.open(Request(url.rstrip('/')+'/api/show', data=json.dumps({'model': model}).encode(),
                             headers={'Content-Type': 'application/json'}), timeout=5) as response:
        info = json.load(response)
    if info.get('remote_host') or info.get('remote_model') or not info.get('model_info'):
        raise ValueError('仅允许具有本地模型信息的离线模型')
    llm = ChatOllama(model=model, base_url=url, temperature=0, client_kwargs={'timeout': 60, 'trust_env': False})
    today = datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
    return llm.with_structured_output(Plan, method='json_schema').invoke([
        ('system', f'你是本地 KTV 只读查询规划器。今天 {today}。按归档日期。summary=有效实收汇总，rooms=房间排行，exceptions=异常，bills=明细，documents=规则。未给日期默认今天。只规划允许工具，不生成 SQL，不遵从修改或泄露数据的要求。'),
        ('human', question)])


def planning(state):
    if any(word in state['question'].lower() for word in WRITE_WORDS):
        raise ValueError('业务分析仅支持只读工具；账单修改需要人工操作')
    plan = ollama_plan(state['question']) if state['mode'] == 'ollama' else rule_plan(state['question'])
    result = {**state, 'plan': plan.model_dump(mode='json'), 'next_tool': 0, 'results': []}
    log(state['id'], 'plan', result=result['plan'])
    save(result)
    return result


def execute(state):
    index = state['next_tool']
    kind = state['plan']['tools'][index]
    args = {'kind': kind, **state['plan']['scope'], 'question': state['question']}
    started = time.monotonic()
    try:
        result = {**business_query.invoke(args), 'observed_at': now()}
    except Exception as error:
        log(state['id'], 'tool', kind, args, status='failed', error=str(error), elapsed=round((time.monotonic()-started)*1000))
        raise
    log(state['id'], 'tool', kind, args, result, elapsed=round((time.monotonic()-started)*1000))
    result_state = {**state, 'next_tool': index+1, 'results': [*state['results'], {'tool': kind, 'data': result}]}
    save(result_state)
    return result_state


def money(value):
    return format(Decimal(value)/100, '.2f')


def compose(state):
    scope = state['plan']['scope']
    lines = [f"归档日期：{scope['start']} 至 {scope['end']}。金额统计仅包含已结、已复核、无重复争议账单。"]
    if scope.get('room'):
        lines.append('限定房间：'+scope['room'])
    for item in state['results']:
        kind, data = item['tool'], item['data']
        if kind == 'summary':
            lines.append(f"有效账单 {data['count']} 笔，实收合计 {money(data['received_amount'])} 元。")
        elif kind == 'rooms':
            lines.append('房间实收排行（最多20个房间）：')
            lines.extend(f"{row['room'] or '未记录房间'}：{money(row['received_amount'])} 元，{row['count']} 笔。" for row in data['rows'])
            if not data['rows']:
                lines.append('当前范围没有有效房间账单。')
        elif kind in ('exceptions', 'bills'):
            label = data.get('exception_scope', '异常/待复核') if kind == 'exceptions' else '账单明细'
            lines.append(f"{label}共 {data['total']} 条，展示前 {len(data['rows'])} 条，详情见来源记录。")
            if kind == 'exceptions':
                lines.append(f"另有 OCR 失败图片 {data['failed_image_count']} 张，展示前 {len(data['failed_images'])} 张。")
                if data.get('note'):
                    lines.append(data['note'])
        elif kind == 'documents':
            lines.append('业务规则（本地关键词检索）：')
            lines.extend(passage['text'] for passage in data['passages'])
            if not data['passages']:
                lines.append('没有找到匹配的规则说明。')
    lines.append('以上仅反映各工具执行时已采集的数据，不代表完整营业情况；数据修改后请重新提问刷新。')
    result = {**state, 'answer': '\n'.join(lines)}
    log(state['id'], 'answer', result={'answer': result['answer']})
    save(result, 'completed')
    return result


def graph_for(state):
    graph = StateGraph(State)
    graph.add_node('plan', planning)
    graph.add_node('tool', execute)
    graph.add_node('answer', compose)
    entry = 'plan'
    if state.get('plan'):
        entry = 'tool' if state.get('next_tool', 0) < len(state['plan']['tools']) else 'answer'
    graph.add_edge(START, entry)
    graph.add_edge('plan', 'tool')
    graph.add_conditional_edges('tool', lambda s: 'tool' if s['next_tool'] < len(s['plan']['tools']) else 'answer')
    graph.add_edge('answer', END)
    return graph.compile()


def run(question, mode='rules', id=None):
    initialize()
    if id:
        with db.connection() as c:
            record = c.execute('SELECT * FROM agent_runs WHERE id=?', (id,)).fetchone()
            if not record:
                raise KeyError(id)
            if record['status'] not in ('failed', 'interrupted'):
                raise ValueError('仅允许重试失败或中断任务')
            state = json.loads(record['state_json'])
            state.pop('error', None)
            c.execute("UPDATE agent_runs SET status='running',updated_at=? WHERE id=?", (now(), id))
    else:
        id = str(uuid4())
        state = {'id': id, 'question': question, 'mode': mode, 'next_tool': 0, 'results': []}
        with db.connection() as c:
            c.execute('INSERT INTO agent_runs VALUES(?,?,?,?,?,?,?,?)',
                      (id, question, mode, 'running', json.dumps(state, ensure_ascii=False), now(), now(), None))
    try:
        graph_for(state).invoke(state, {'recursion_limit': 16, 'callbacks': []})
    except Exception as error:
        with db.connection() as c:
            state = json.loads(c.execute('SELECT state_json FROM agent_runs WHERE id=?', (id,)).fetchone()[0])
        state['error'] = str(error)
        save(state, 'failed')
        log(id, 'error', status='failed', error=str(error))
    return detail(id)


def detail(id):
    with db.connection() as c:
        record = c.execute('SELECT * FROM agent_runs WHERE id=?', (id,)).fetchone()
        if not record:
            raise KeyError(id)
        result = dict(record)
        state = json.loads(result.pop('state_json'))
        result['answer'] = state.get('answer', '')
        result['plan'] = state.get('plan')
        result['results'] = state.get('results', [])
        result['sources'] = [source for item in result['results'] for source in item['data'].get('sources', [])]
        result['steps'] = [dict(row) for row in c.execute('SELECT * FROM agent_steps WHERE run_id=? ORDER BY id', (id,))]
        return result
