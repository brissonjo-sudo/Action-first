import json
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_manifests_and_skill_are_consistent(self) -> None:
        codex = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        claude = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        skill = (ROOT / "skills" / "action-first" / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(codex["name"], "action-first")
        self.assertEqual(claude["name"], "action-first")
        self.assertIn("name: action-first", skill)
        self.assertIn("uniquement quand l'utilisateur invoque Action First", skill)

    def test_codex_invocation_is_explicit(self) -> None:
        config = (ROOT / "skills" / "action-first" / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("allow_implicit_invocation: false", config)

    def test_required_content_is_not_sacrificed(self) -> None:
        skill = (ROOT / "skills" / "action-first" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("conserver toutes les étapes et informations nécessaires", skill)
        self.assertIn("confirmation avant une action destructive", skill)

    def test_release_archive_is_reproducible(self) -> None:
        spec = importlib.util.spec_from_file_location("build_release", ROOT / "scripts" / "build_release.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        _, first = module.build()
        _, second = module.build()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
