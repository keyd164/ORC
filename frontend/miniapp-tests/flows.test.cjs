const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../miniapp');

function harness(name, routes = () => ({}), overrides = {}) {
  let definition;
  const app = { globalData: { baseUrl: 'http://192.168.1.10:8000/api/v1' } };
  const storage = {}, calls = [], timers = new Map();
  const wx = {
    request(o) { calls.push(o); Promise.resolve().then(() => { try { o.success({ statusCode: 200, data: routes(o) }); } catch (e) { o.success({ statusCode: e.status || 500, data: { detail: e.message } }); } }); },
    showModal(o) { o.success({ confirm: true }); }, showToast() {},
    getStorageSync(k) { return storage[k]; }, setStorageSync(k, v) { storage[k] = v; },
    navigateTo(o) { calls.push({ navigation: 'push', ...o }); }, switchTab(o) { calls.push({ navigation: 'tab', ...o }); },
    previewImage(o) { calls.push(o); }, env: { USER_DATA_PATH: '/local' },
    ...overrides
  };
  const context = vm.createContext({ wx, getApp: () => app, Page: d => { definition = d; }, console,
    setInterval(fn) { const id = timers.size + 1; timers.set(id, fn); return id; }, clearInterval(id) { timers.delete(id); } });
  const cache = new Map();
  function load(file) {
    file = path.resolve(file);
    if (cache.has(file)) return cache.get(file).exports;
    const module = { exports: {} }; cache.set(file, module);
    const fn = vm.runInContext('(function(require,module,exports){' + fs.readFileSync(file, 'utf8') + '\n})', context, { filename: file });
    fn(p => load(path.resolve(path.dirname(file), p + (path.extname(p) ? '' : '.js'))), module, module.exports);
    return module.exports;
  }
  if (name) load(path.join(root, 'pages', name, 'index.js'));
  const page = definition ? { ...definition, data: JSON.parse(JSON.stringify(definition.data)), setData(update) {
    for (const [key, value] of Object.entries(update)) {
      const parts = key.replace(/\[(\d+)\]/g, '.$1').split('.');
      let obj = this.data;
      for (const part of parts.slice(0, -1)) obj = obj[part];
      obj[parts.at(-1)] = value;
    }
  } } : null;
  return { page, app, wx, storage, calls, timers, load };
}

test('home has two working entry routes and settings persist a validated address', async () => {
  const h = harness('home'); h.page.collect(); h.page.manage();
  assert.deepEqual(h.calls.map(x => x.navigation), ['push', 'tab']);
  const api = h.load(path.join(root, 'utils/api.js'));
  assert.throws(() => api.setServer('javascript:bad'));
  assert.equal(api.setServer('http://192.168.1.2:8000/'), 'http://192.168.1.2:8000/api/v1');
  assert.equal(h.storage.ktvServer, h.app.globalData.baseUrl);
  assert.equal(api.query({ room: 'V 11', min_amount: 0, end: '' }), 'room=V%2011&min_amount=0');
});

test('multi-image upload continues after failure and retries only unsuccessful images', async () => {
  const uploaded = []; let attempts = 0;
  const h = harness('upload', () => ({ id: 'batch' }), {
    uploadFile(o) {
      uploaded.push(o.filePath); const fail = o.filePath === 'bad' && attempts++ === 0;
      queueMicrotask(() => fail ? o.fail({ errMsg: 'network failed' }) : o.success({ statusCode: 200, data: JSON.stringify({ status: o.filePath === 'duplicate' ? 'duplicate' : 'queued', image_id: o.filePath }) }));
      return { onProgressUpdate(fn) { fn({ progress: 100 }); } };
    }
  });
  h.page.data.files = ['ok', 'bad', 'duplicate'].map((f, i) => ({ uid: i, path: f, size: 20, state: 'pending' }));
  await h.page.upload();
  assert.deepEqual(h.page.data.files.map(f => f.state), ['uploaded', 'failed', 'duplicate']);
  await h.page.upload();
  assert.deepEqual(uploaded, ['ok', 'bad', 'duplicate', 'bad']);
  assert.equal(h.page.data.files[1].state, 'uploaded');
  assert.equal(h.page.data.busy, false);
});

test('detail loads by image, preserves unsaved work and submits only explicit corrections', async () => {
  const writes = [];
  const bill = { id: 'b', image_id: 'i', received_amount: 8001, cashier: '张', review_status: 'pending', duplicate_status: 'none', fields: [], edit_logs: [], issues: [] };
  const h = harness('detail', o => {
    if (o.method === 'PATCH') { writes.push(o.data); return bill; }
    if (o.url.endsWith('/images/i')) return { id: 'i', bill_id: 'b', status: 'completed' };
    if (o.url.endsWith('/bills/b')) return bill;
    if (o.url.endsWith('/fields')) return { received_amount: '实收金额', cashier: '收银员' };
    if (o.url.endsWith('/ocr-runs')) return [];
    throw Error('Unexpected URL ' + o.url);
  });
  h.page.onLoad({ id: 'i' }); await h.page.refresh();
  assert.equal(h.page.data.fields[0].value, '80.01');
  h.page.clear({ currentTarget: { dataset: { index: 1 } } });
  const count = h.calls.length; await h.page.refresh();
  assert.equal(h.calls.length, count); assert.equal(h.page.data.dirty, true);
  await h.page.save();
  assert.deepEqual(JSON.parse(JSON.stringify(writes[0].fields)), { cashier: null });
  assert.equal(h.page.data.dirty, false);
});

test('detail review explicitly acknowledges anomalies and blocks unsaved changes', async () => {
  const calls = [];
  const h = harness('detail', o => { calls.push(o); return {}; });
  h.page.billId = 'b'; h.page.fetchData = async () => {};
  h.page.data.dirty = true; await h.page.review();
  assert.equal(calls.length, 0); assert.match(h.page.data.error, /保存/);
  h.page.data.dirty = false; h.page.data.issues = ['实收与应收不一致'];
  await h.page.review();
  assert.equal(calls[0].data.confirm_all, true);
  assert.equal(calls[0].data.acknowledge_issues, true);
});

test('bill filtering converts yuan accurately and rejects reversed bounds', () => {
  const h = harness('bills');
  h.page.data.filters.min = '0.01'; h.page.data.filters.max = '80.10';
  assert.equal(h.page.params().min_amount, 1); assert.equal(h.page.params().max_amount, 8010);
  h.page.data.filters.min = '1.001'; assert.throws(() => h.page.params(), /两位小数/);
  h.page.data.filters.min = '90'; assert.throws(() => h.page.params(), /最低金额/);
});

test('record polling stops when the page hides and pagination appends', async () => {
  const h = harness('records', o => o.url.includes('offset=0') ? [{ id: '1', status: 'queued', received_amount: null }] : [{ id: '2', status: 'completed', received_amount: 20 }]);
  h.page.onShow(); await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.timers.size, 1); assert.equal(h.page.data.rows[0].money, '—');
  await h.page.more(); assert.equal(h.page.data.rows.length, 2);
  h.page.onHide(); assert.equal(h.timers.size, 0);
});

test('non-2xx download is rejected before opening a file', async () => {
  const h = harness(null, undefined, { downloadFile(o) { o.success({ statusCode: 500, tempFilePath: '/bad' }); } });
  const api = h.load(path.join(root, 'utils/api.js'));
  await assert.rejects(api.download('/exports/bills', 'x.xlsx'), /下载失败/);
});

test('business analysis defaults to rules mode and source links open bill details', async () => {
  const result = { id: 'run-1', status: 'completed', sources: [{kind:'bill',id:'bill-1',label:'R1'}], steps:[], answer:'合计 80.00 元' };
  const h = harness('agent', o => o.method === 'POST' ? result : []);
  await h.page.ask();
  const request = h.calls.find(c => c.method === 'POST');
  assert.equal(request.data.mode, 'rules');
  assert.equal(h.page.data.result.answer, '合计 80.00 元');
  h.page.source({currentTarget:{dataset:{index:0}}});
  assert.equal(h.calls.at(-1).url, '/pages/detail/index?bill_id=bill-1');
});
