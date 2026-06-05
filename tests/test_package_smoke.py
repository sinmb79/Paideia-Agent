from __future__ import annotations

import importlib
import tomllib
import unittest
from pathlib import Path


class PackageSmokeTests(unittest.TestCase):
    def _pyproject(self) -> dict:
        return tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    def test_console_script_entrypoints_are_importable_callables(self) -> None:
        project = self._pyproject()["project"]
        scripts = project.get("scripts", {})

        self.assertEqual(
            scripts,
            {
                "ai22b-doctor": "ai22b.doctor:main",
                "ai22b-bigram": "ai22b.from_scratch.bigram:main",
                "ai22b-talent-foundry": "ai22b.talent_foundry.cli:main",
            },
        )
        for target in scripts.values():
            module_name, function_name = target.split(":")
            function = getattr(importlib.import_module(module_name), function_name)
            self.assertTrue(callable(function), target)

    def test_optional_dependencies_are_split_by_runtime_capability(self) -> None:
        project = self._pyproject()["project"]
        optional = project.get("optional-dependencies", {})

        self.assertEqual(project["name"], "paideia-agent")
        self.assertEqual(project["requires-python"], ">=3.10")
        self.assertEqual(project.get("dependencies", []), [])
        self.assertIn("pytest", optional["dev"])
        self.assertIn("openai>=1.0.0", optional["live-llm"])
        self.assertIn("transformers", optional["local-llm"])
        self.assertIn("chromadb", optional["rag"])
        self.assertIn("peft", optional["fine-tune"])

        capability_packages = set().union(
            optional["live-llm"],
            optional["local-llm"],
            optional["rag"],
            optional["fine-tune"],
            optional["dev"],
        )
        self.assertTrue(capability_packages <= set(optional["all"]))

    def test_package_metadata_does_not_reference_private_or_local_paths(self) -> None:
        pyproject_text = Path("pyproject.toml").read_text(encoding="utf-8")
        forbidden_fragments = [
            "C:\\Users\\",
            "/Users/",
            "file://",
            "../",
            "data/private",
            "models/",
            ".env",
        ]
        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, pyproject_text)


if __name__ == "__main__":
    unittest.main()
