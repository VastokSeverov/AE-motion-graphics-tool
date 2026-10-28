"""Unit tests for the Ollama-backed planner without requiring a running model."""
import importlib.util
import json
import pathlib
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ollama_planner", ROOT / "server" / "ollama_planner.py")
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({"message": {"content": json.dumps(self.payload)}}).encode()


class OllamaPlannerTests(unittest.TestCase):
    def proposal(self, **overrides):
        data = {
            "action": "animated_text", "text": "Hello World", "prefix": "AI — ",
            "duration": 1.2, "color": "white", "explanation": "Create animated text with the entrance."
        }
        data.update(overrides)
        return data

    @patch.object(planner.urllib.request, "urlopen")
    def test_validates_and_returns_reviewable_plan(self, mock_urlopen):
        mock_urlopen.return_value = FakeResponse(self.proposal())
        plan = planner.plan_request('Make a bold title that says "Hello World" and animate it over 1.2 seconds')
        self.assertEqual(plan["action"], "animated_text")
        self.assertEqual(plan["text"], "Hello World")
        self.assertEqual(plan["duration"], 1.2)
        self.assertEqual(plan["color"], "white")
        self.assertTrue(plan["requires_confirmation"])
        self.assertEqual(plan["planner"], "ollama")
        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode())
        self.assertEqual(payload["model"], "qwen3:14b")
        self.assertEqual(payload["stream"], False)

    @patch.object(planner.urllib.request, "urlopen")
    def test_rejects_unsupported_model_proposal(self, mock_urlopen):
        mock_urlopen.return_value = FakeResponse(self.proposal(action="arbitrary_script"))
        with self.assertRaises(planner.PlanningError):
            planner.plan_request("Do something")

    @patch.object(planner.urllib.request, "urlopen")
    def test_rejects_out_of_range_duration(self, mock_urlopen):
        mock_urlopen.return_value = FakeResponse(self.proposal(duration=99))
        with self.assertRaises(planner.PlanningError):
            planner.plan_request("Animate this")


    @patch.object(planner.urllib.request, "urlopen")
    def test_accepts_supported_text_color(self, mock_urlopen):
        mock_urlopen.return_value = FakeResponse(self.proposal(color="red"))
        plan = planner.plan_request('Create red animated text saying Hello')
        self.assertEqual(plan["color"], "red")

    @patch.object(planner.urllib.request, "urlopen")
    def test_rejects_unsupported_text_color(self, mock_urlopen):
        mock_urlopen.return_value = FakeResponse(self.proposal(color="ultraviolet"))
        with self.assertRaises(planner.PlanningError):
            planner.plan_request("Create ultraviolet text")

    def test_rejects_empty_and_oversized_prompts_before_network(self):
        with patch.object(planner.urllib.request, "urlopen") as mock_urlopen:
            for prompt in ("", "  ", "x" * 1001):
                with self.assertRaises(planner.PlanningError):
                    planner.plan_request(prompt)
            mock_urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
