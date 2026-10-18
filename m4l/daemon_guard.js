/**
 * Vibelton Arranger Daemon Guard for Max for Live node.script
 *
 * Keeps the local Vibelton server (http://127.0.0.1:8765) running. On load it
 * pings /api/status; if nothing answers it resolves the repo and a working
 * Python, spawns `python -m vibelton.server`, captures its output in
 * ~/.vibelton/logs/server.log and reports a readable error to Max on failure.
 *
 * Config (optional): ~/.vibelton/config.json
 *   { "repo_path": "/path/to/vibelton", "python_path": "/path/to/python3", "port": 8765 }
 * Environment overrides: VIBELTON_PATH, VIBELTON_PYTHON, VIBELTON_HOME, VIBELTON_PORT.
 */

const http = require('http');
const childProcess = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

let maxApi = null;
try {
  maxApi = require('max-api');
} catch (e) {
  maxApi = null; // standalone Node.js (CLI / tests)
}

// Bump whenever daemon_guard.js, autoresize.js or the .maxpat changes: the device reports this to the
// server so it can tell you when the device loaded in Live is older than the one on disk.
const DEVICE_VERSION = '2026-10-18-arranger-8';
const SERVER_HOST = '127.0.0.1';
const STARTUP_ATTEMPTS = 20; // x 500ms = 10s
const MIN_PYTHON = '3.11'; // the server test suite is verified on Python 3.11, 3.12 and 3.14

function vibeltonHome(env = process.env) {
  return env.VIBELTON_HOME || path.join(os.homedir(), '.vibelton');
}

function logPath(env = process.env) {
  return path.join(vibeltonHome(env), 'logs', 'server.log');
}

function loadConfig(env = process.env, fsApi = fs) {
  try {
    const parsed = JSON.parse(fsApi.readFileSync(path.join(vibeltonHome(env), 'config.json'), 'utf8'));
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch (e) {
    return {};
  }
}

function serverPort(env = process.env, config = {}) {
  const port = Number(env.VIBELTON_PORT || config.port || 8765);
  return Number.isInteger(port) && port > 0 && port < 65536 ? port : 8765;
}

function readSessionToken(env = process.env) {
  try {
    return fs.readFileSync(path.join(vibeltonHome(env), 'session_token'), 'utf8').trim();
  } catch (e) {
    return '';
  }
}

/**
 * Repo path order: VIBELTON_PATH -> config.repo_path -> relative to the device.
 * Returns { path, source } or { path: null, tried: [...] }.
 */
function resolveRepoPath({ env = process.env, config = {}, scriptDir = __dirname, exists = fs.existsSync } = {}) {
  const candidates = [
    ['VIBELTON_PATH', env.VIBELTON_PATH],
    ['config.json', config.repo_path],
    ['relative to device', path.resolve(scriptDir, '..')],
    ['relative to device', path.resolve(scriptDir, '..', '..')]
  ].filter(([, p]) => p);
  const tried = [];
  for (const [source, candidate] of candidates) {
    tried.push(candidate);
    if (exists(path.join(candidate, 'vibelton', 'server.py'))) {
      return { path: candidate, source };
    }
  }
  return { path: null, tried };
}

/** Default runner: execFileSync returning { ok, stdout, stderr }. */
function defaultRunner(file, args, timeout = 5000) {
  try {
    const stdout = childProcess.execFileSync(file, args, {
      timeout, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe']
    });
    return { ok: true, stdout: String(stdout), stderr: '' };
  } catch (err) {
    return { ok: false, stdout: String(err.stdout || ''), stderr: String(err.stderr || err.message || '') };
  }
}

/**
 * Find a Python that actually runs and is at least MIN_PYTHON.
 * /usr/bin/python3 goes last and is only tried if the developer tools are
 * installed (otherwise macOS pops the Xcode / license dialog).
 */
function resolvePython({ env = process.env, config = {}, run = defaultRunner, exists = fs.existsSync } = {}) {
  const candidates = [
    ['VIBELTON_PYTHON', env.VIBELTON_PYTHON],
    ['PYTHON', env.PYTHON],
    ['config.json', config.python_path],
    ['homebrew', '/opt/homebrew/bin/python3'],
    ['/usr/local', '/usr/local/bin/python3'],
    ['PATH', 'python3'],
    ['system', '/usr/bin/python3']
  ].filter(([, p]) => p);
  const rejected = [];
  const check = `import sys; print(sys.version_info >= (${MIN_PYTHON.replace('.', ', ')}))`;
  for (const [source, candidate] of candidates) {
    if (candidate.startsWith('/') && !exists(candidate)) {
      rejected.push(`${candidate}: not found`);
      continue;
    }
    if (candidate === '/usr/bin/python3') {
      const dev = run('/usr/bin/xcode-select', ['-p'], 3000);
      if (!dev.ok) {
        rejected.push(`${candidate}: skipped (Xcode command line tools not installed)`);
        continue;
      }
    }
    const result = run(candidate, ['-c', check]);
    if (result.ok && result.stdout.trim() === 'True') {
      return { python: candidate, source, rejected };
    }
    rejected.push(`${candidate}: ${result.ok ? 'older than ' + MIN_PYTHON : (result.stderr.trim().split('\n')[0] || 'failed to run')}`);
  }
  return { python: null, rejected };
}

function tailLog(file, lines = 8) {
  try {
    return fs.readFileSync(file, 'utf8').trimEnd().split('\n').slice(-lines).join('\n');
  } catch (e) {
    return '';
  }
}

/** Keep the user's home directory out of messages and logs they may paste into a bug report. */
function redactHome(text, home = os.homedir()) {
  const value = String(text);
  return home && home !== '/' ? value.split(home).join('~') : value;
}

function sendToMax(...args) {
  if (maxApi && typeof maxApi.outlet === 'function') {
    maxApi.outlet(...args);
  } else {
    console.log('[daemon_guard]', ...args);
  }
}

/** Report a startup failure: machine-readable code plus a human sentence. */
function reportError(code, message) {
  const safe = redactHome(message);
  sendToMax('status', 'error');
  sendToMax('error_code', code);
  sendToMax('error', safe);
  sendToMax('offline_url', offlineUrl(code, safe));
}

/** Self-contained "server offline" page, as a fully percent-encoded data URL. */
function offlineUrl(code, message, env = process.env) {
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
  const html = '<body style="margin:0;padding:14px;background:#1e1e1e;color:#ddd;font:12px -apple-system,sans-serif">' +
    '<b style="color:#e6d765">Server offline</b> <code>' + esc(code) + '</code>' +
    '<p>' + esc(message) + '</p><p>Log: <code>' + esc(logPath(env)) + '</code></p>' +
    '<button onclick="window.max&&window.max.outlet(\'retry\')">Retry</button></body>';
  return 'data:text/html;charset=utf-8,' + encodeURIComponent(html).replace(/[!'()*]/g, (c) => '%' + c.charCodeAt(0).toString(16));
}

/**
 * Ping /api/status. Distinguishes: ok (Vibelton), not_vibelton (port taken by
 * something that answers but is not Vibelton), down (nothing listening).
 */
function pingStatus(timeoutMs = 1500, port = serverPort(process.env, loadConfig())) {
  return new Promise((resolve) => {
    const req = http.get({ host: SERVER_HOST, port, path: '/api/status', timeout: timeoutMs }, (res) => {
      let raw = '';
      res.on('data', (chunk) => { raw += chunk; });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(raw);
          if (res.statusCode === 200 && parsed && typeof parsed === 'object' && 'state' in parsed) {
            resolve({ ok: true, data: parsed });
            return;
          }
        } catch (err) { /* fall through */ }
        resolve({ ok: false, reason: 'not_vibelton', statusCode: res.statusCode });
      });
    });
    req.on('timeout', () => { req.destroy(); resolve({ ok: false, reason: 'timeout', error: 'timeout' }); });
    req.on('error', (err) => resolve({ ok: false, reason: 'down', error: err.code || err.message }));
  });
}

/** Tell the server which device version is actually loaded in Live (best effort, needs the session token). */
function announceDevice(port = serverPort(process.env, loadConfig())) {
  const body = JSON.stringify({ device_version: DEVICE_VERSION });
  const req = http.request({
    host: SERVER_HOST, port, path: '/api/device/hello', method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body), 'X-Vibelton-Token': readSessionToken() }
  }, (res) => { res.resume(); });
  req.on('error', () => {});
  req.end(body);
}

function sendConnected(ping, { reload = false, port = serverPort(process.env, loadConfig()) } = {}) {
  sendToMax('status', 'connected');
  sendToMax('device_version', DEVICE_VERSION);
  announceDevice(port);
  // After a (re)start the jweb may have loaded before the server existed.
  if (reload) sendToMax('server_url', `http://${SERVER_HOST}:${port}/arranger_device.html`);
  if (ping.data && ping.data.state) {
    sendToMax('bridge_connected', Boolean(ping.data.state.connected));
    sendToMax('tempo', ping.data.state.tempo || 120);
  }
}

let isSpawning = false;

async function spawnServer() {
  if (isSpawning) return;
  isSpawning = true;
  try {
    sendToMax('status', 'starting_server');
    const config = loadConfig();
    const port = serverPort(process.env, config);

    const existing = await pingStatus(1500, port);
    if (existing.ok) { sendConnected(existing); return; }
    if (existing.reason === 'not_vibelton' || existing.reason === 'timeout') {
      reportError('port_in_use', `Port ${port} is in use by another program that is not Vibelton. Quit it or set "port" in ~/.vibelton/config.json.`);
      return;
    }

    const repo = resolveRepoPath({ env: process.env, config });
    if (!repo.path) {
      reportError('repo_not_found', `Vibelton repo not found. Set VIBELTON_PATH or "repo_path" in ${path.join(vibeltonHome(), 'config.json')}. Tried: ${repo.tried.join(', ')}`);
      return;
    }
    const py = resolvePython({ env: process.env, config });
    if (!py.python) {
      reportError('python_not_found', `No working Python ${MIN_PYTHON}+ found. Set "python_path" in config.json. ${py.rejected.join('; ')}`);
      return;
    }
    sendToMax('python', py.python);
    sendToMax('repo', repo.path);

    const log = logPath();
    fs.mkdirSync(path.dirname(log), { recursive: true });
    const fd = fs.openSync(log, 'a');
    fs.writeSync(fd, `\n--- ${new Date().toISOString()} starting ${redactHome(py.python)} -m vibelton.server in ${redactHome(repo.path)}\n`);
    let exited = null;
    const child = childProcess.spawn(py.python, ['-m', 'vibelton.server'], {
      cwd: repo.path,
      detached: true,
      stdio: ['ignore', fd, fd],
      env: Object.assign({}, process.env, {
        PATH: `/opt/homebrew/bin:/usr/local/bin:${process.env.PATH || ''}`,
        VIBELTON_DAEMON: '1',
        PYTHONUNBUFFERED: '1',
        VIBELTON_PORT: String(port)
      })
    });
    child.on('error', (err) => { exited = { code: null, message: err.message }; });
    child.on('exit', (code) => { exited = { code }; });
    child.unref();
    fs.closeSync(fd);

    for (let i = 0; i < STARTUP_ATTEMPTS; i++) {
      await new Promise((r) => setTimeout(r, 500));
      const ping = await pingStatus(1000, port);
      if (ping.ok) {
        sendToMax('server_started', true);
        sendConnected(ping, { reload: true, port });
        return;
      }
      if (exited) break;
    }
    // A second device racing us may already have a server up on the port (ours then exits: no fallback port).
    const last = await pingStatus(1500, port);
    if (last.ok) {
      sendToMax('server_started', true);
      sendConnected(last, { reload: true, port });
      return;
    }
    const tail = tailLog(log);
    if (exited) {
      reportError('server_crashed', `Server exited (${exited.message || 'code ' + exited.code}). Last log lines: ${tail}`);
    } else {
      reportError('startup_timeout', `Server did not answer within 10s. Last log lines: ${tail}`);
    }
  } catch (err) {
    reportError('spawn_failed', String(err.message || err));
  } finally {
    isSpawning = false;
  }
}

const WATCHDOG_MS = 5000;
const WATCHDOG_MAX_QUICK_RETRIES = 3;
const WATCHDOG_BACKOFF_MS = 60000;

function newWatchdogState() {
  return { failures: 0, nextAt: 0 };
}

/**
 * One watchdog step: if the server is down, start it again; after a few failed restarts wait a minute
 * between tries. Makes recovery independent of the Retry button's path through the jweb page and Max.
 */
async function watchdogTick(state, { ping, spawn }, now = Date.now()) {
  if (now < state.nextAt) return;
  const result = await ping();
  if (result.ok) { state.failures = 0; state.nextAt = 0; return; }
  state.failures += 1;
  await spawn();
  if (state.failures >= WATCHDOG_MAX_QUICK_RETRIES) state.nextAt = now + WATCHDOG_BACKOFF_MS;
}

async function checkOrStart() {
  const ping = await pingStatus(1500);
  if (ping.ok) {
    sendConnected(ping);
  } else {
    await spawnServer();
  }
}

/**
 * Ask the server to open the floating studio window. This must NOT send 'open_popout' back to Max: that
 * message is routed to the 'popout' message box, which calls this handler again, in an endless loop.
 */
function requestPopout({ request = http.request, port = serverPort(process.env, loadConfig()) } = {}) {
  const req = request({
    host: SERVER_HOST,
    port,
    path: '/api/popout',
    method: 'POST',
    headers: { 'X-Vibelton-Token': readSessionToken() }
  }, () => {});
  req.on('error', () => {});
  req.end();
}

if (maxApi && typeof maxApi.addHandlers === 'function') {
  maxApi.addHandlers({
    loadbang: () => { checkOrStart(); },
    check: async () => {
      const ping = await pingStatus(1500);
      if (ping.ok) sendConnected(ping); else sendToMax('status', 'offline');
    },
    start: () => { spawnServer(); },
    retry: () => { spawnServer(); },
    popout: () => { requestPopout(); }
  });
}

// Initial auto-check (skipped when required by tests)
if (require.main === module || maxApi) {
  checkOrStart();
}
if (maxApi) {
  const watchdog = newWatchdogState();
  setInterval(() => { watchdogTick(watchdog, { ping: () => pingStatus(1500), spawn: spawnServer }).catch(() => {}); }, WATCHDOG_MS);
}

module.exports = {
  DEVICE_VERSION,
  announceDevice,
  pingStatus,
  resolvePython,
  resolveRepoPath,
  loadConfig,
  logPath,
  offlineUrl,
  redactHome,
  requestPopout,
  newWatchdogState,
  watchdogTick,
  checkOrStart,
  spawnServer
};
