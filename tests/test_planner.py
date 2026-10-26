"""Unit tests for the constrained natural-language planner."""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("vasto_planner", ROOT / "server" / "planner.py")
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)


class PlannerTests(unittest.TestCase):
    def test_animated_text_extracts_text_and_duration(self):
        plan = planner.plan_request('Create animated text saying "Hello World" in 1.2 seconds')
        self.assertEqual(plan["action"], "animated_text")
        self.assertEqual(plan["text"], "Hello World")
        self.assertEqual(plan["duration"], 1.2)
        self.assertTrue(plan["requires_confirmation"])

    def test_shape_is_allowlisted(self):
        plan = planner.plan_request("Make a rounded rectangle shape")
        self.assertEqual(plan["action"], "shape")

    def test_glass_discloses_limitation(self):
        plan = planner.plan_request("Create a liquid glass starter")
        self.assertEqual(plan["action"], "liquid_glass")
        self.assertIn("does not simulate physical refraction", plan["explanation"])

    def test_organize_prefix(self):
        plan = planner.plan_request("Prefix selected layers with BG")
        self.assertEqual(plan["action"], "organize")
        self.assertEqual(plan["prefix"], "BG")

    def test_unsupported_request_is_rejected(self):
        with self.assertRaises(planner.PlanningError):
            planner.plan_request("Remove the background and download a Pinterest video")

    def test_empty_and_oversized_requests_are_rejected(self):
        for prompt in ("", " "):
            with self.assertRaises(planner.PlanningError):
                planner.plan_request(prompt)
        with self.assertRaises(planner.PlanningError):
            planner.plan_request("x" * 1001)


if __name__ == "__main__":
    unittest.main()
