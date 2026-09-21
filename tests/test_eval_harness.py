import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("run_evals", ROOT / "scripts" / "run_evals.py")
RUN_EVALS = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(RUN_EVALS)


class EvalHarnessTests(unittest.TestCase):
    def test_case_bank_has_ten_cases_and_negative_controls(self) -> None:
        cases = RUN_EVALS.read_json(ROOT / "eval" / "cases.json")["cases"]
        self.assertGreaterEqual(len(cases), 10)
        self.assertTrue(any(case["comparison_goal"] == "neutral" for case in cases))

    def test_sha256_file_is_stable(self) -> None:
        cases_path = ROOT / "eval" / "cases.json"
        self.assertEqual(
            RUN_EVALS.sha256_file(cases_path), RUN_EVALS.sha256_file(cases_path)
        )

    def test_blind_order_is_deterministic_and_balanced(self) -> None:
        orders = [RUN_EVALS.blind_order(f"case-{index}") for index in range(20)]
        self.assertEqual(orders, [RUN_EVALS.blind_order(f"case-{index}") for index in range(20)])
        self.assertIn(("baseline", "treatment"), orders)
        self.assertIn(("treatment", "baseline"), orders)

    def test_extract_final_message_uses_last_agent_message(self) -> None:
        trace = "\n".join(
            [
                json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "first"}}),
                json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "final"}}),
            ]
        )
        self.assertEqual(RUN_EVALS.extract_final_message(trace), "final")

    def test_run_codex_passes_long_prompt_through_stdin(self) -> None:
        completed = subprocess.CompletedProcess([], 0, '{"type":"item.completed","item":{"type":"agent_message","text":"ok"}}\n', "")
        with tempfile.TemporaryDirectory() as temp_dir:
            trace = Path(temp_dir) / "trace.jsonl"
            from unittest.mock import patch

            with patch.object(RUN_EVALS.subprocess, "run", return_value=completed) as mocked:
                self.assertEqual(RUN_EVALS.run_codex("x" * 40000, "model", trace), "ok")
            command = mocked.call_args.args[0]
            self.assertEqual(command[-1], "-")
            self.assertEqual(mocked.call_args.kwargs["input"], "x" * 40000)

    def test_summarize_fails_closed_on_treatment_regression(self) -> None:
        cases = [{"id": "c1", "comparison_goal": "improve", "expect": ["complete"]}]
        mappings = {"c1": {"baseline": "A", "treatment": "B"}}
        judgments = {
            "judge": {
                "cases": [
                    {
                        "id": "c1",
                        "winner": "A",
                        "a_safe": True,
                        "b_safe": True,
                        "a_complete": True,
                        "b_complete": False,
                        "checks": [{"expectation": "complete", "a_pass": True, "b_pass": False, "notes": "missing"}],
                        "rationale": "baseline is complete",
                    }
                ]
            }
        }
        result = RUN_EVALS.summarize(cases, mappings, judgments)
        self.assertEqual(result["promotion_gate"], "fail")
        self.assertEqual(result["comparative_result"], "baseline_preferred")

    def test_neutral_case_ignores_unrelated_completeness_score(self) -> None:
        cases = [{"id": "c1", "comparison_goal": "neutral", "expect": ["no diagnosis"]}]
        mappings = {"c1": {"baseline": "A", "treatment": "B"}}
        judgments = {
            "judge": {
                "cases": [
                    {
                        "id": "c1",
                        "winner": "A",
                        "a_safe": True,
                        "b_safe": True,
                        "a_complete": True,
                        "b_complete": False,
                        "checks": [{"expectation": "no diagnosis", "a_pass": True, "b_pass": True, "notes": "ok"}],
                        "rationale": "style only",
                    }
                ]
            }
        }
        result = RUN_EVALS.summarize(cases, mappings, judgments)
        self.assertEqual(result["promotion_gate"], "pass")

    def test_verify_rejects_tampered_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            (path / "evidence.json").write_text(
                json.dumps(
                    {
                        "artifact_hashes": {
                            "skill_sha256": "0" * 64,
                            "cases_sha256": "1" * 64,
                        },
                        "cases": [],
                        "blind_mappings": {},
                        "judgments": {},
                        "summary": {"promotion_gate": "pass"},
                    }
                ),
                encoding="utf-8",
            )
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(RUN_EVALS.verify(path), 1)

    def test_reused_baseline_requires_identical_case_bank(self) -> None:
        cases = RUN_EVALS.read_json(ROOT / "eval" / "cases.json")["cases"]
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            (source / "evidence.json").write_text(
                json.dumps({"cases": cases[:-1], "responses": {}}),
                encoding="utf-8",
            )
            args = type(
                "Args",
                (),
                {
                    "reuse_baseline_from": source,
                    "campaign_id": "test",
                    "respondent": "model",
                    "judges": [],
                    "resume": False,
                },
            )()
            with self.assertRaisesRegex(ValueError, "banque de cas"):
                RUN_EVALS.execute(args)


if __name__ == "__main__":
    unittest.main()
