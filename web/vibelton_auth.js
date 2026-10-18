// Adds the per-session token to same-origin state-changing requests.
// The token is injected into the served HTML as <meta name="vibelton-token">.
(function () {
  const nativeFetch = window.fetch.bind(window);
  let token = null;

  function metaToken() {
    const meta = document.querySelector('meta[name="vibelton-token"]');
    return meta ? meta.getAttribute('content') : null;
  }

  async function refreshToken() {
    const res = await nativeFetch('/api/session-token');
    if (!res.ok) throw new Error('Could not obtain session token');
    token = (await res.json()).token;
    return token;
  }

  function needsToken(url, method) {
    const parsed = new URL(url, window.location.href);
    if (parsed.origin !== window.location.origin) return false;
    return method !== 'GET' && method !== 'HEAD' || parsed.pathname === '/api/popout';
  }

  window.fetch = async function (input, init) {
    const request = new Request(input, init);
    const method = request.method.toUpperCase();
    if (!needsToken(request.url, method)) return nativeFetch(input, init);
    const attempt = async (tok) => {
      const headers = new Headers(request.headers);
      headers.set('X-Vibelton-Token', tok);
      return nativeFetch(new Request(request.clone(), { headers }));
    };
    token = token || metaToken() || await refreshToken();
    let response = await attempt(token);
    if (response.status === 403) {
      // Server may have restarted and issued a new token.
      const body = await response.clone().json().catch(() => ({}));
      if (/token/i.test(body.error || '')) {
        response = await attempt(await refreshToken());
      }
    }
    return response;
  };
})();
