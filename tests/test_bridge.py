""""Integration tests for the loopback bridge; no After Effects installation required."""
import importlib.util
import json
import pathlib
import threading
import urllib.error
import urllib.request
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("vasto_server", ROOT / "server" / "server.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = bridge.ThreadingHTTPServer(("127.0.0.1", 0), bridge.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:%s" % cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        with bridge._lock:
            bridge._queue.clear()
            bridge._commands.clear()
            bridge._results.clear()
            bridge._inflight_id = None
            bridge._last_heartbeat = 0

    def request(self, path, data=None):
        body = None if data is None else json.dumps(data).encode()
        req = urllib.request.Request(self.base + path, data=body,
            headers={"Content-Type": "application/json"} if body is not None else {})
        try:
            with urllib.request.urlopen(req, timeout=3) as res:
                return res.status, json.loads(res.read().decode())
        except urllib.error.HTTPError as err:
            try:
                return err.code, json.loads(err.read().decode())
            finally:
                err.close()

    def test_rejects_unknown_action(self):
        status, data = self.request("/api/command", {"action": "arbitrary_script"})
        self.assertEqual(status, 400)
        self.assertIn("error", data)

    def test_command_requires_result_before_next_delivery(self):
        status, queued = self.request("/api/command", {"action": "shape"})
        self.assertEqual(status, 202)
        self.assertEqual(queued["status"], "queued")
        status, first = self.request("/api/next")
        self.assertEqual(first["command"]["id"], queued["id"])
        status, second = self.request("/api/next")
        self.assertIsNone(second["command"])
        self.assertTrue(second["busy"])
        status, result = self.request("/api/result", {
            "id": queued["id"], "status": "succeeded", "message": "SUCCESS: test"
        })
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "succeeded")
        status, final = self.request("/api/status")
        self.assertEqual(final["results"][-1]["status"], "succeeded")
        status, next_poll = self.request("/api/next")
        self.assertFalse(next_poll["busy"])

    def test_unknown_result_id_is_rejected(self):
        status, data = self.request("/api/result", {
            "id": "not-a-command", "status": "succeeded", "message": "fake"
        })
        self.assertEqual(status, 404)

    def test_failed_command_is_recorded(self):
        _, queued = self.request("/api/command", {"action": "organize"})
        _, delivered = self.request("/api/next")
        status, result = self.request("/api/result", {
            "id": delivered["command"]["id"], "status": "failed",
            "message": "ERROR: no layers selected"
        })
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "failed")
        _, state = self.request("/api/status")
        self.assertEqual(state["results"][-1]["message"], "ERROR: no layers selected")

if __name__ == "__main__":
    unittest.main()
