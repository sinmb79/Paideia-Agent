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

    def test_public_release_license_and_metadata_are_declared(self) -> None:
        project = self._pyproject()["project"]
        license_file = Path("LICENSE")

        self.assertTrue(license_file.exists())
        self.assertIn("MIT License", license_file.read_text(encoding="utf-8"))
        self.assertEqual(project.get("license", {}).get("file"), "LICENSE")
        self.assertIn("License :: OSI Approved :: MIT License", project.get("classifiers", []))
        self.assertEqual(project.get("urls", {}).get("Repository"), "https://github.com/sinmb79/Paideia-Agent")
        self.assertTrue(Path("SECURITY.md").exists())
        self.assertTrue(Path("README.ko.md").exists())
        self.assertTrue(Path("docs/public_release_readiness.md").exists())
        self.assertTrue(Path("docs/public_release_readiness.ko.md").exists())

    def test_public_release_readiness_audit_passes_without_network_or_subprocess(self) -> None:
        from ai22b.talent_foundry.public_release import audit_public_release_readiness

        report = audit_public_release_readiness(Path("."))

        self.assertEqual(report["schema"], "paideia-public-release-readiness/v1")
        self.assertTrue(report["passed"])
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["summary"]["failed_count"], 0)
        self.assertGreater(report["summary"]["public_candidate_file_count"], 20)
        self.assertEqual(report["summary"]["public_candidate_issue_count"], 0)
        self.assertFalse(report["summary"]["network_call_performed"])
        self.assertFalse(report["summary"]["subprocess_executed"])
        self.assertFalse(report["summary"]["private_runtime_outputs_scanned"])
        self.assertFalse(report["policy"]["secret_values_exported"])
        check_by_id = {item["id"]: item for item in report["checks"]}
        self.assertTrue(check_by_id["public_candidate_content_scan"]["passed"])
        self.assertEqual(check_by_id["public_candidate_content_scan"]["details"]["issue_count"], 0)


if __name__ == "__main__":
    unittest.main()
