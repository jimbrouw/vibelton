const test = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const dg = require('../m4l/daemon_guard.js');

const exists = (...present) => (p) => present.includes(p);

test('repo path: VIBELTON_PATH wins over config and relative', () => {
  const r = dg.resolveRepoPath({
    env: { VIBELTON_PATH: '/env/repo' }, config: { repo_path: '/cfg/repo' }, scriptDir: '/dev/m4l',
    exists: exists('/env/repo/vibelton/server.py', '/cfg/repo/vibelton/server.py', '/dev/vibelton/server.py')
  });
  assert.deepStrictEqual(r, { path: '/env/repo', source: 'VIBELTON_PATH' });
});

test('repo path: config file used when env unset', () => {
  const r = dg.resolveRepoPath({
    env: {}, config: { repo_path: '/cfg/repo' }, scriptDir: '/dev/m4l',
    exists: exists('/cfg/repo/vibelton/server.py')
  });
  assert.strictEqual(r.path, '/cfg/repo');
  assert.strictEqual(r.source, 'config.json');
});

test('repo path: falls back to path relative to device', () => {
  const r = dg.resolveRepoPath({
    env: {}, config: {}, scriptDir: '/some/repo/m4l', exists: exists('/some/repo/vibelton/server.py')
  });
  assert.deepStrictEqual(r, { path: '/some/repo', source: 'relative to device' });
});

test('repo path: invalid env falls through; nothing found lists what was tried', () => {
  const r = dg.resolveRepoPath({ env: { VIBELTON_PATH: '/gone' }, config: {}, scriptDir: '/x/m4l', exists: () => false });
  assert.strictEqual(r.path, null);
  assert.ok(r.tried.includes('/gone'));
  assert.ok(!JSON.stringify(r).includes('/Users/standard'), 'no hard-coded user path');
});

test('python: skips a candidate that exists but does not run', () => {
  const calls = [];
  const run = (file) => {
    calls.push(file);
    return file === '/opt/homebrew/bin/python3'
      ? { ok: false, stdout: '', stderr: 'bad interpreter' }
      : { ok: true, stdout: 'True\n', stderr: '' };
  };
  const r = dg.resolvePython({ env: {}, config: {}, run, exists: exists('/opt/homebrew/bin/python3', '/usr/local/bin/python3') });
  assert.strictEqual(r.python, '/usr/local/bin/python3');
  assert.match(r.rejected[0], /bad interpreter/);
});

test('python: rejects versions below the tested minimum', () => {
  const run = (file) => ({ ok: true, stdout: file === 'python3' ? 'True\n' : 'False\n', stderr: '' });
  const r = dg.resolvePython({ env: {}, config: {}, run, exists: exists('/opt/homebrew/bin/python3') });
  assert.strictEqual(r.python, 'python3');
  assert.match(r.rejected[0], /older than/);
});

test('python: config python_path is preferred over homebrew', () => {
  const run = () => ({ ok: true, stdout: 'True\n', stderr: '' });
  const r = dg.resolvePython({ env: {}, config: { python_path: '/custom/py' }, run, exists: exists('/custom/py', '/opt/homebrew/bin/python3') });
  assert.deepStrictEqual([r.python, r.source], ['/custom/py', 'config.json']);
});

test('python: /usr/bin/python3 skipped when Xcode tools missing (no dialog triggered)', () => {
  const seen = [];
  const run = (file, args) => {
    seen.push(file);
    if (file === '/usr/bin/xcode-select') return { ok: false, stdout: '', stderr: 'error' };
    return { ok: false, stdout: '', stderr: 'nope' };
  };
  const r = dg.resolvePython({ env: {}, config: {}, run, exists: exists('/usr/bin/python3') });
  assert.strictEqual(r.python, null);
  assert.ok(!seen.includes('/usr/bin/python3'), 'system python must not be executed');
  assert.ok(r.rejected.some((m) => /Xcode/.test(m)));
});

test('config file: missing or malformed gives empty config', () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'vib-'));
  assert.deepStrictEqual(dg.loadConfig({ VIBELTON_HOME: home }), {});
  fs.writeFileSync(path.join(home, 'config.json'), '{not json');
  assert.deepStrictEqual(dg.loadConfig({ VIBELTON_HOME: home }), {});
  fs.writeFileSync(path.join(home, 'config.json'), JSON.stringify({ repo_path: '/r' }));
  assert.deepStrictEqual(dg.loadConfig({ VIBELTON_HOME: home }), { repo_path: '/r' });
});

test('ping distinguishes a non-Vibelton listener from a dead port', async () => {
  const http = require('node:http');
  const srv = http.createServer((req, res) => { res.end('<html>hello</html>'); });
  await new Promise((r) => srv.listen(0, '127.0.0.1', r));
  const port = srv.address().port;
  const other = await dg.pingStatus(1000, port);
  assert.strictEqual(other.reason, 'not_vibelton');
  await new Promise((r) => srv.close(r));
  const down = await dg.pingStatus(1000, port);
  assert.strictEqual(down.reason, 'down');
});

test('offline data URL is a single token with no spaces, commas after the prefix, or semicolons', () => {
  const url = dg.offlineUrl('python_not_found', 'No <working> Python');
  assert.match(url, /^data:text\/html;charset=utf-8,/);
  const body = url.slice(url.indexOf(',') + 1);
  assert.ok(!/[\s,;<>]/.test(body));
});

test('home directory is redacted from messages and the offline page', () => {
  assert.strictEqual(dg.redactHome('/Users/jo/Documents/vibelton/x.py failed', '/Users/jo'), '~/Documents/vibelton/x.py failed');
  assert.strictEqual(dg.redactHome('/Users/jo and /Users/jo/y', '/Users/jo'), '~ and ~/y');
  assert.strictEqual(dg.redactHome('nothing here', '/Users/jo'), 'nothing here');
  assert.strictEqual(dg.redactHome('/etc/hosts', '/'), '/etc/hosts', 'a root home must not rewrite every path');
});

test('popout request never echoes open_popout back to Max (that message routes straight back into popout)', () => {
  const sent = [];
  const posts = [];
  const fakeRequest = (options, cb) => ({ on() {}, end() { posts.push(options.path); } });
  dg.requestPopout({ request: fakeRequest, port: 1 });
  assert.deepStrictEqual(posts, ['/api/popout']);
  assert.ok(!sent.some((args) => args[0] === 'open_popout'), 'echoing open_popout loops forever');
});

test('watchdog restarts a dead server, resets when it is back, and backs off after repeated failures', async () => {
  const calls = [];
  let alive = false;
  const deps = { ping: async () => ({ ok: alive }), spawn: async () => { calls.push('spawn'); } };
  const state = dg.newWatchdogState();
  await dg.watchdogTick(state, deps, 0);
  assert.deepStrictEqual(calls, ['spawn'], 'dead server is restarted');
  await dg.watchdogTick(state, deps, 5000);
  await dg.watchdogTick(state, deps, 10000);
  assert.strictEqual(calls.length, 3);
  await dg.watchdogTick(state, deps, 15000);
  assert.strictEqual(calls.length, 3, 'after 3 failed restarts it waits instead of hammering');
  await dg.watchdogTick(state, deps, 15000 + 61000);
  assert.strictEqual(calls.length, 4, 'tries again after the back-off');
  alive = true;
  await dg.watchdogTick(state, deps, 140000);
  assert.strictEqual(state.failures, 0);
  assert.strictEqual(calls.length, 4);
});
