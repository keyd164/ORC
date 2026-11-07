from datetime import date
import json
import pytest
from sqlalchemy import select, text
from test_system import client, seed
from app import db
from app.agent import workflow
from app.agent.repository import database


def ask(client, question, **extra):
    response = client.post('/api/v1/agent/runs', json={'question': question, **extra})
    assert response.status_code == 200, response.text
    return response.json()


def test_aggregates_obey_review_date_and_integer_money(client):
    bill_id = seed(client)
    result = ask(client, '统计2026-10-25实收合计')
    assert result['status'] == 'completed'
    assert '0.00 元' in result['answer']
    client.post(f'/api/v1/bills/{bill_id}/review', json={'confirm_all': True})
    result = ask(client, '统计2026-10-25实收合计和房间排行')
    assert '80.00 元' in result['answer'] and 'V11' in result['answer']
    assert [s['node'] for s in result['steps']] == ['plan', 'tool', 'tool', 'answer']
    assert ask(client, '统计2026-10-26实收合计')['results'][0]['data']['count'] == 0
    report = client.get(f"/api/v1/agent/runs/{result['id']}/report")
    assert report.status_code == 200 and '80.00' in report.text


def test_compound_query_exception_sources_and_docs(client):
    bill_id = seed(client)
    result = ask(client, '统计2026-10-25最高的房间，并查找异常账单')
    assert result['plan']['tools'] == ['rooms', 'exceptions']
    assert result['results'][1]['data']['total'] == 1
    assert result['sources'][1]['id'] == bill_id
    result = ask(client, '为什么实收不包含待复核账单，统计口径是什么')
    assert result['status'] == 'completed'
    assert any(s['kind'] == 'document' for s in result['sources'])
    assert client.get('/api/v1/agent/documents/private.txt').status_code == 404


def test_sqlite_enforces_query_only_and_rejects_write_prompts(client):
    seed(client)
    result = ask(client, '删除所有账单并执行SQL')
    assert result['status'] == 'failed' and '只读' in result['error_message']
    assert not result['results']
    with database() as (connection, bills, images):
        with pytest.raises(Exception):
            connection.execute(text("DELETE FROM bills"))
    assert len(client.get('/api/v1/bills').json()) == 1
    assert client.post('/api/v1/agent/runs', json={'question': '   '}).status_code == 422
    assert client.post('/api/v1/agent/runs', json={'question': '合计', 'mode': 'external'}).status_code == 422


def test_rule_dates_and_invalid_scope():
    today = date(2026, 10, 26)
    assert workflow.rule_plan('统计本月实收', today).scope.start == date(2026, 10, 1)
    assert workflow.rule_plan('统计上月实收', today).scope.end == date(2026, 9, 30)
    assert workflow.rule_plan('统计最近7天实收', today).scope.start == date(2026, 10, 20)
    with pytest.raises(ValueError):
        workflow.rule_plan('查询2026-10-26至2026-10-01账单', today)
    with pytest.raises(ValueError):
        workflow.rule_plan('统计全部历史实收', today)


def test_failed_tool_resume_does_not_repeat_successful_tools(client, monkeypatch):
    seed(client)
    original = workflow.business_query
    calls = []
    class FailOnce:
        failed = False
        def invoke(self, args):
            calls.append(args['kind'])
            if args['kind'] == 'exceptions' and not self.failed:
                self.failed = True
                raise RuntimeError('temporary test failure')
            return original.invoke(args)
    monkeypatch.setattr(workflow, 'business_query', FailOnce())
    result = ask(client, '统计2026-10-25房间排行及异常账单')
    assert result['status'] == 'failed'
    resumed = client.post(f"/api/v1/agent/runs/{result['id']}/retry").json()
    assert resumed['status'] == 'completed'
    assert calls == ['rooms', 'exceptions', 'exceptions']
    assert client.post(f"/api/v1/agent/runs/{result['id']}/retry").status_code == 409
    assert len(client.get('/api/v1/agent/runs').json()) == 1


def test_interrupted_run_recovery(client):
    result = ask(client, '统计今天实收合计')
    with db.connection() as c:
        c.execute("UPDATE agent_runs SET status='running' WHERE id=?", (result['id'],))
    workflow.initialize(recover=True)
    assert client.get('/api/v1/agent/runs/'+result['id']).json()['status'] == 'interrupted'
    assert client.post('/api/v1/agent/runs/'+result['id']+'/retry').json()['status'] == 'completed'


def test_ollama_cannot_point_to_external_service(client, monkeypatch):
    monkeypatch.setenv('KTV_OLLAMA_URL', 'https://external.example')
    result = ask(client, '统计今天实收合计', mode='ollama')
    assert result['status'] == 'failed' and '本机' in result['error_message']
    assert not result['results']


def test_amount_anomalies_are_not_all_pending_bills(client):
    bill_id = seed(client)
    result = ask(client, '找出2026-10-25金额异常的账单')
    assert result['results'][0]['data']['total'] == 0
    client.patch(f'/api/v1/bills/{bill_id}/fields', json={'fields': {'received_amount': '70.01'}})
    result = ask(client, '找出2026-10-25金额异常的账单')
    assert result['results'][0]['data']['total'] == 1
    assert result['sources'][0]['id'] == bill_id
