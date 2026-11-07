"""Evaluate rule routing against a fixed public fixture; no real bill access."""
import json
import sys
from datetime import date
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root/'backend'))
from app.agent.workflow import rule_plan

fixture = json.loads((root/'backend/tests/fixtures/agent_tasks.json').read_text(encoding='utf8'))
results = []
for case in fixture['cases']:
    try:
        plan = rule_plan(case['question'], date.fromisoformat(fixture['reference_date']))
        passed = (not case.get('reject') and plan.tools == case['tools']
                  and str(plan.scope.start) == case['start'] and str(plan.scope.end) == case['end'])
        results.append({'question': case['question'], 'passed': passed, 'plan': plan.model_dump(mode='json')})
    except ValueError as error:
        results.append({'question': case['question'], 'passed': bool(case.get('reject')), 'error': str(error)})
output = root/'data/exports/rules-evaluation.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps({'scope': fixture['scope'], 'passed': sum(r['passed'] for r in results),
                              'total': len(results), 'cases': results}, ensure_ascii=False, indent=2), encoding='utf8')
print(f"Rule routing: {sum(r['passed'] for r in results)}/{len(results)}; report: {output}")
raise SystemExit(0 if all(r['passed'] for r in results) else 1)
