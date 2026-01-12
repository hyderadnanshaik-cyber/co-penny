from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print('--- /health ---')
print(client.get('/health').json())

print('--- /selftest ---')
st = client.get('/selftest').json()
print({k: st[k] for k in list(st)[:6]})

print('--- /historical/analyze ---')
payload = { session_id:test,message:expenditure analysis from 2019,context:[]}
resp = client.post('/historical/analyze', json=payload).json()
print({'status': resp.get('status'), 'type': resp.get('type'), 'has_charts': bool(resp.get('charts'))})
