from __future__ import annotations

import json
import os
import stat
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from vibelton import security


class ServerSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.env = patch.dict(os.environ, {"VIBELTON_HOME": cls.tmp.name})
        cls.env.start()
        # server.py loads .env.local into os.environ on import; keep that scoped to this class.
        global server
        from vibelton import server
        cls.token = security.issue_token()
        cls.httpd, cls.port = server.create_server()
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.env.stop()
        cls.tmp.cleanup()

    def call(self, method, path, body=None, headers=None):
        req = urllib.request.Request(self.base + path, method=method, headers=headers or {},
                                     data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(req) as res:
                return res.status, dict(res.headers), res.read()
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read()

    def test_binds_loopback_only(self):
        self.assertEqual(self.httpd.server_address[0], "127.0.0.1")

    def test_post_without_token_is_403(self):
        status, _, body = self.call("POST", "/api/production/rollback", {})
        self.assertEqual(status, 403)
        self.assertIn("token", json.loads(body)["error"])

    def test_post_with_wrong_token_is_403(self):
        status, _, _ = self.call("POST", "/api/production/rollback", {}, {security.TOKEN_HEADER: "nope"})
        self.assertEqual(status, 403)

    def test_post_with_valid_token_passes_guard(self):
        status, _, _ = self.call("POST", "/api/production/analyse", {}, {security.TOKEN_HEADER: self.token})
        self.assertNotEqual(status, 403)

    def test_every_post_route_requires_token(self):
        for path in ("/api/chat", "/api/feedback", "/api/popout", "/api/composition/apply",
                     "/api/samples/import", "/api/production/apply", "/api/production/rollback", "/api/device/hello"):
            status, _, _ = self.call("POST", path, {})
            self.assertEqual(status, 403, path)

    def test_popout_get_requires_token(self):
        status, _, _ = self.call("GET", "/api/popout")
        self.assertEqual(status, 403)

    def test_foreign_origin_rejected_even_with_token(self):
        status, headers, _ = self.call("POST", "/api/production/analyse", {},
                                       {security.TOKEN_HEADER: self.token, "Origin": "https://evil.example"})
        self.assertEqual(status, 403)
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_foreign_origin_gets_no_cors_header_on_get(self):
        status, headers, _ = self.call("GET", "/api/status", headers={"Origin": "https://evil.example"})
        self.assertEqual(status, 200)
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertNotEqual(headers.get("Access-Control-Allow-Origin"), "*")

    def test_preflight_foreign_origin_denied(self):
        status, headers, _ = self.call("OPTIONS", "/api/production/apply", headers={"Origin": "https://evil.example"})
        self.assertEqual(status, 403)
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_own_origin_gets_specific_cors(self):
        origin = f"http://127.0.0.1:{self.port}"
        _, headers, _ = self.call("GET", "/api/status", headers={"Origin": origin})
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), origin)

    def test_foreign_host_header_rejected(self):
        status, _, _ = self.call("GET", "/api/status", headers={"Host": "evil.example"})
        self.assertEqual(status, 403)

    def test_status_get_needs_no_token(self):
        status, _, _ = self.call("GET", "/api/status")
        self.assertEqual(status, 200)

    def test_html_gets_token_injected_not_in_url(self):
        status, _, body = self.call("GET", "/arranger_device.html")
        self.assertEqual(status, 200)
        self.assertIn(f'name="vibelton-token" content="{self.token}"'.encode(), body)

    def test_session_token_endpoint_same_origin_only(self):
        status, _, body = self.call("GET", "/api/session-token")
        self.assertEqual((status, json.loads(body)["token"]), (200, self.token))
        status, _, _ = self.call("GET", "/api/session-token", headers={"Origin": "https://evil.example"})
        self.assertEqual(status, 403)

    def test_errors_come_with_a_plain_explanation_and_never_a_traceback(self):
        status, _, body = self.call("POST", "/api/production/rollback", {})
        data = json.loads(body)
        self.assertEqual(403, status)
        self.assertEqual("session_expired", data["explanation"]["code"])
        status, _, body = self.call("POST", "/api/production/rollback", {}, {security.TOKEN_HEADER: self.token})
        data = json.loads(body)
        self.assertEqual(400, status)
        self.assertIn("explanation", data)
        self.assertNotIn("Traceback", body.decode())

    def test_versions_endpoint_is_readable_and_the_device_hello_needs_the_token(self):
        status, _, body = self.call("GET", "/api/versions")
        self.assertEqual(200, status)
        self.assertIn("warnings", json.loads(body))
        status, _, _ = self.call("POST", "/api/device/hello", {"device_version": "d-test"})
        self.assertEqual(403, status)
        status, _, _ = self.call("POST", "/api/device/hello", {"device_version": "d-test"}, {security.TOKEN_HEADER: self.token})
        self.assertEqual(200, status)
        loaded = json.loads(self.call("GET", "/api/versions")[2])["device"]["loaded"]
        self.assertEqual("d-test", loaded)

    def test_security_headers_are_on_every_response(self):
        for path in ("/api/status", "/arranger_device.html"):
            _, headers, _ = self.call("GET", path)
            self.assertEqual("nosniff", headers.get("X-Content-Type-Options"), path)
            self.assertEqual("SAMEORIGIN", headers.get("X-Frame-Options"), path)
            self.assertEqual("no-referrer", headers.get("Referrer-Policy"), path)

    def test_oversized_bodies_are_refused_before_being_read(self):
        import http.client
        for path, limit_label in (("/api/chat", "small"), ("/api/composition/save", "large")):
            conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
            conn.putrequest("POST", path)
            conn.putheader("Content-Length", str(security.MAX_BODY_BYTES + 1 if limit_label == "large" else security.SMALL_BODY_BYTES + 1))
            conn.putheader(security.TOKEN_HEADER, self.token)
            conn.endheaders()
            self.assertEqual(413, conn.getresponse().status, path)
            conn.close()

    def test_a_flood_of_state_changing_requests_is_rate_limited(self):
        security.reset_rate_limit()
        with patch.object(security, "RATE_LIMIT_PER_MINUTE", 3):
            statuses = [self.call("POST", "/api/feedback", {"rating": "up"}, {security.TOKEN_HEADER: self.token})[0] for _ in range(5)]
        security.reset_rate_limit()
        self.assertEqual([429, 429], statuses[-2:])
        self.assertNotIn(429, statuses[:3])

    def test_reads_are_not_rate_limited(self):
        security.reset_rate_limit()
        with patch.object(security, "RATE_LIMIT_PER_MINUTE", 1):
            self.assertEqual([200] * 5, [self.call("GET", "/api/status")[0] for _ in range(5)])
        security.reset_rate_limit()

    def test_the_server_never_opens_a_browser_unless_asked(self):
        self.assertFalse(server.should_open_browser({}))
        self.assertTrue(server.should_open_browser({"VIBELTON_OPEN_BROWSER": "1"}))
        self.assertFalse(server.should_open_browser({"VIBELTON_OPEN_BROWSER": "1", "VIBELTON_DAEMON": "1"}))

    def test_token_file_is_private(self):
        path = Path(self.tmp.name) / "session_token"
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(path.read_text(), self.token)


if __name__ == "__main__":
    unittest.main()


class PopoutNeverLaunchesBrowserTests(unittest.TestCase):
    def test_popout_does_not_launch_a_browser_by_default(self) -> None:
        from unittest.mock import MagicMock, patch
        from vibelton import server
        handler = MagicMock()
        with patch.dict('os.environ', {}, clear=False), patch('subprocess.Popen') as popen, patch('webbrowser.open') as opener:
            import os
            os.environ.pop('VIBELTON_POPOUT_BROWSER', None)
            server.Handler.handle_popout(handler)
        popen.assert_not_called()
        opener.assert_not_called()
        self.assertEqual('not_opened', handler.send_json.call_args[0][0]['status'])


class DaemonPortTests(unittest.TestCase):
    def test_daemon_never_falls_back_to_another_port(self) -> None:
        import socket
        from unittest.mock import patch
        from vibelton import server
        blocker = socket.socket()
        blocker.bind(('127.0.0.1', 0))
        blocker.listen(1)
        busy = blocker.getsockname()[1]
        self.addCleanup(blocker.close)
        with patch.object(server, 'PORT', busy), patch.dict('os.environ', {'VIBELTON_DAEMON': '1'}):
            with self.assertRaises(RuntimeError):
                server.create_server()
        with patch.object(server, 'PORT', busy), patch.dict('os.environ', {'VIBELTON_DAEMON': ''}):
            httpd, port = server.create_server()   # interactive runs may still pick the next free port
            httpd.server_close()
            self.assertGreater(port, busy)
