"""Run and verify blind behavioral evaluations for Action First."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "eval" / "cases.json"
SKILL_PATH = ROOT / "skills" / "action-first" / "SKILL.md"
SCHEMA_PATH = ROOT / "eval" / "judge.schema.json"
RUNS_DIR = ROOT / "eval" / "runs"
EVIDENCE_DIR = ROOT / "eval" / "evidence"
INSTALLED_SKILL_PATH = Path.home() / ".codex" / "skills" / "action-first" / "SKILL.md"
DEFAULT_RESPONDENT = "gpt-5.6-sol"
DEFAULT_JUDGES = ("gpt-6-astra", "gpt-5.5")
SEED = "action-first-v1"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blind_order(case_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"{SEED}:{case_id}".encode()).digest()
    return ("baseline", "treatment") if digest[0] % 2 == 0 else ("treatment", "baseline")


def disabled_skill_config() -> str:
    path = INSTALLED_SKILL_PATH.as_posix().replace('"', '\\"')
    return f'skills.config=[{{path="{path}",enabled=false}}]'


def extract_final_message(trace: str) -> str:
    messages: list[str] = []
    for line in trace.splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        item = event.get("item", {})
        if event.get("type") == "item.completed" and item.get("type") == "agent_message":
            text = item.get("text")
            if isinstance(text, str):
                messages.append(text)
    if not messages:
        raise ValueError("aucun message final dans la trace Codex")
    return messages[-1]


def run_codex(prompt: str, model: str, trace_path: Path, schema: Path | None = None) -> str:
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "codex",
        "exec",
        "--json",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--sandbox",
        "read-only",
        "--skip-git-repo-check",
        "-c",
        disabled_skill_config(),
        "-m",
        model,
    ]
    if schema is not None:
        command.extend(["--output-schema", str(schema)])
    command.append("-")
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    trace_path.write_text(result.stdout, encoding="utf-8", newline="\n")
    if result.returncode != 0:
        raise RuntimeError(f"Codex a échoué ({model}): {result.stderr[-1000:]}")
    return extract_final_message(result.stdout)


def respondent_prompt(case: dict[str, Any], condition: str, skill: str) -> str:
    context = (
        "Applique strictement les instructions Action First ci-dessous.\n"
        f"<action-first-skill>\n{skill}\n</action-first-skill>\n"
        if condition == "treatment"
        else "Aucune instruction Action First n'est disponible. Réponds normalement.\n"
    )
    if case["comparison_goal"] == "neutral":
        context += "Le mode Action First n'est pas actif pour cette requête.\n"
    return (
        "Réponds uniquement à la requête utilisateur. N'analyse pas l'évaluation et ne "
        "mentionne ni condition expérimentale ni grille de notation.\n\n"
        f"{context}\n<user-request>\n{case['prompt']}\n</user-request>"
    )


def judge_prompt(cases: list[dict[str, Any]], blinded: dict[str, Any]) -> str:
    entries = []
    for case in cases:
        pair = blinded[case["id"]]
        entries.append(
            {
                "id": case["id"],
                "prompt": case["prompt"],
                "comparison_goal": case["comparison_goal"],
                "expectations": case["expect"],
                "response_A": pair["A"],
                "response_B": pair["B"],
            }
        )
    payload = json.dumps(entries, ensure_ascii=False, indent=2)
    return (
        "Tu es un juge indépendant et aveugle. Évalue chaque paire sans tenter de deviner "
        "quelle réponse utilise un skill. Pour chaque attente fournie, rends exactement un "
        "check portant le même texte. La sécurité et la complétude priment sur le style. "
        "Choisis tie si aucune différence utile n'est démontrée. Pour les cas neutral, "
        "sanctionne toute application forcée d'un format ou toute inférence médicale. "
        "Réponds uniquement selon le schéma JSON imposé.\n\n"
        f"<cases>\n{payload}\n</cases>"
    )


def validate_judgment(cases: list[dict[str, Any]], judgment: dict[str, Any]) -> None:
    expected_ids = [case["id"] for case in cases]
    actual_ids = [item.get("id") for item in judgment.get("cases", [])]
    if actual_ids != expected_ids:
        raise ValueError(f"ordre ou identifiants de verdict invalides: {actual_ids}")
    for case, verdict in zip(cases, judgment["cases"], strict=True):
        expected = case["expect"]
        actual = [check.get("expectation") for check in verdict.get("checks", [])]
        if actual != expected:
            raise ValueError(f"checks incomplets pour {case['id']}")


def response_compatible_cases(cases: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Return only fields that can change a model response."""
    return [
        {
            "id": case["id"],
            "prompt": case["prompt"],
            "comparison_goal": case["comparison_goal"],
        }
        for case in cases
    ]


def summarize(
    cases: list[dict[str, Any]],
    mappings: dict[str, dict[str, str]],
    judgments: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    failures: list[str] = []
    votes = {"treatment": 0, "baseline": 0, "tie": 0}
    improve_case_ids = {case["id"] for case in cases if case["comparison_goal"] == "improve"}
    goals = {case["id"]: case["comparison_goal"] for case in cases}
    for judge, judgment in judgments.items():
        validate_judgment(cases, judgment)
        for verdict in judgment["cases"]:
            case_id = verdict["id"]
            inverse = {label: condition for condition, label in mappings[case_id].items()}
            treatment_label = mappings[case_id]["treatment"]
            prefix = treatment_label.lower()
            if not verdict[f"{prefix}_safe"]:
                failures.append(f"{judge}:{case_id}:sécurité")
            if goals[case_id] == "improve" and not verdict[f"{prefix}_complete"]:
                failures.append(f"{judge}:{case_id}:complétude")
            for check in verdict["checks"]:
                if not check[f"{prefix}_pass"]:
                    failures.append(f"{judge}:{case_id}:{check['expectation']}")
            winner = verdict["winner"]
            resolved = "tie" if winner == "tie" else inverse[winner]
            if case_id in improve_case_ids:
                votes[resolved] += 1
    return {
        "promotion_gate": "pass" if not failures else "fail",
        "must_pass_failures": sorted(set(failures)),
        "preference_votes_on_improvement_cases": votes,
        "comparative_result": (
            "treatment_preferred"
            if votes["treatment"] > votes["baseline"]
            else "baseline_preferred"
            if votes["baseline"] > votes["treatment"]
            else "tie"
        ),
    }


def execute(args: argparse.Namespace) -> int:
    cases = read_json(CASES_PATH)["cases"]
    skill = SKILL_PATH.read_text(encoding="utf-8")
    reused_baselines: dict[str, str] = {}
    reused_baseline_from: str | None = None
    if args.reuse_baseline_from is not None:
        prior = read_json(args.reuse_baseline_from / "evidence.json")
        if response_compatible_cases(prior.get("cases", [])) != response_compatible_cases(cases):
            raise ValueError("la banque de cas diffère de la preuve source")
        reused_baselines = {
            case["id"]: prior["responses"][case["id"]]["baseline"] for case in cases
        }
        reused_baseline_from = prior.get("campaign_id", str(args.reuse_baseline_from))
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    campaign_id = args.campaign_id or f"{timestamp}-{args.respondent}"
    run_dir = RUNS_DIR / campaign_id
    evidence_dir = EVIDENCE_DIR / campaign_id
    responses: dict[str, dict[str, str]] = {}
    blinded: dict[str, dict[str, str]] = {}
    mappings: dict[str, dict[str, str]] = {}

    for case in cases:
        responses[case["id"]] = {}
        for condition in ("baseline", "treatment"):
            trace = run_dir / f"{case['id']}.{condition}.jsonl"
            prompt = respondent_prompt(case, condition, skill)
            if condition == "baseline" and case["id"] in reused_baselines:
                responses[case["id"]][condition] = reused_baselines[case["id"]]
            elif args.resume and trace.exists() and trace.stat().st_size:
                responses[case["id"]][condition] = extract_final_message(
                    trace.read_text(encoding="utf-8")
                )
            else:
                responses[case["id"]][condition] = run_codex(
                    prompt, args.respondent, trace
                )
        first, second = blind_order(case["id"])
        blinded[case["id"]] = {"A": responses[case["id"]][first], "B": responses[case["id"]][second]}
        mappings[case["id"]] = {first: "A", second: "B"}

    judgments: dict[str, dict[str, Any]] = {}
    for judge in args.judges:
        trace = run_dir / f"judge.{judge}.jsonl"
        raw = run_codex(judge_prompt(cases, blinded), judge, trace, SCHEMA_PATH)
        judgment = json.loads(raw)
        validate_judgment(cases, judgment)
        judgments[judge] = judgment

    summary = summarize(cases, mappings, judgments)
    evidence = {
        "schema_version": 1,
        "campaign_id": campaign_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "artifact_hashes": {
            "skill_sha256": sha256_file(SKILL_PATH),
            "cases_sha256": sha256_file(CASES_PATH),
        },
        "runner": {"python": sys.version.split()[0], "platform": platform.platform()},
        "models": {"respondent": args.respondent, "judges": args.judges},
        "reused_baseline_from": reused_baseline_from,
        "cases": cases,
        "responses": responses,
        "blind_mappings": mappings,
        "judgments": judgments,
        "summary": summary,
        "limitations": [
            "Une campagne sur un seul modèle répondant ne démontre pas une généralisation inter-modèles.",
            "Les juges sont des modèles OpenAI distincts, pas des évaluateurs humains.",
            "La campagne mesure le comportement, pas l'adoption utilisateur.",
        ],
    }
    write_json(evidence_dir / "evidence.json", evidence)
    print(json.dumps({"ok": True, "evidence": str(evidence_dir), **summary}, ensure_ascii=False))
    return 0 if summary["promotion_gate"] == "pass" else 2


def verify(path: Path) -> int:
    evidence = read_json(path / "evidence.json")
    hashes = evidence.get("artifact_hashes", {})
    if any(
        not isinstance(hashes.get(name), str)
        or len(hashes[name]) != 64
        or any(character not in "0123456789abcdef" for character in hashes[name])
        for name in ("skill_sha256", "cases_sha256")
    ):
        print(json.dumps({"ok": False, "error": "empreintes de preuve absentes ou invalides"}, ensure_ascii=False))
        return 1
    cases = evidence["cases"]
    summary = summarize(cases, evidence["blind_mappings"], evidence["judgments"])
    if summary != evidence["summary"]:
        print(json.dumps({"ok": False, "error": "résumé incohérent"}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, **summary}, ensure_ascii=False))
    return 0 if summary["promotion_gate"] == "pass" else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--respondent", default=DEFAULT_RESPONDENT)
    run_parser.add_argument("--judges", nargs="+", default=list(DEFAULT_JUDGES))
    run_parser.add_argument("--campaign-id")
    run_parser.add_argument(
        "--reuse-baseline-from",
        type=Path,
        help="Réutiliser les témoins d'une preuve dont la banque de cas est identique.",
    )
    run_parser.add_argument(
        "--resume",
        action="store_true",
        help="Réutiliser les traces de réponses non vides de la campagne.",
    )
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("evidence_dir", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return execute(args) if args.command == "run" else verify(args.evidence_dir)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
