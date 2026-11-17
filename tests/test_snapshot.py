import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SnapshotTests(unittest.TestCase):
    def test_public_templates_exclude_credentials_and_old_paths(self):
        forbidden_keys = {
            "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY", "apiKey",
            "access_token", "refresh_token", "password", "apiKeyHelper",
        }

        def inspect(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden_keys.intersection(value))
                for child in value.values():
                    inspect(child)
            elif isinstance(value, list):
                for child in value:
                    inspect(child)

        for path in (ROOT / "templates").rglob("*"):
            if not path.is_file():
                continue
            with self.subTest(template=path.relative_to(ROOT)):
                text = path.read_text(encoding="utf-8")
                self.assertNotRegex(text, r"(?i)[a-z]:[/\\]users[/\\]")
                if path.suffix == ".json":
                    inspect(json.loads(text))

    def test_official_gpt_route_and_unconfigured_api_routes(self):
        settings = json.loads((ROOT / "templates/t3/settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["defaultModelSelection"]["instanceId"], "codex")
        self.assertEqual(settings["providerInstances"]["codex"]["driver"], "codex")
        manifest = json.loads((ROOT / "templates/manifest.json").read_text(encoding="utf-8"))
        for provider_id in manifest["providers"]:
            self.assertFalse(settings["providerInstances"][provider_id]["enabled"])

    def test_real_snapshot_restores_and_accepts_local_key_without_exporting_it(self):
        with tempfile.TemporaryDirectory(prefix="y3code-snapshot-") as temporary:
            home = Path(temporary) / "new user home"
            t3_home = Path(temporary) / "custom t3 home"
            prefix = [sys.executable, str(ROOT / "scripts/restore.py"), "--home", str(home), "--t3-home", str(t3_home)]

            def run(*args):
                result = subprocess.run(prefix + list(args), capture_output=True, encoding="utf-8", timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return result.stdout + result.stderr

            run("--with-agent-rules")
            self.assertFalse(home.exists())
            self.assertFalse(t3_home.exists())
            run("--with-agent-rules", "--apply")
            before = {p: p.read_bytes() for directory in (home, t3_home) for p in directory.rglob("*") if p.is_file()}
            output = run("--with-agent-rules", "--apply")
            self.assertNotIn("create:", output)
            self.assertNotIn("update:", output)
            self.assertEqual(before, {p: p.read_bytes() for directory in (home, t3_home) for p in directory.rglob("*") if p.is_file()})

            token = "synthetic-test-credential-do-not-log"
            secret_file = Path(temporary) / "private-key.txt"
            secret_file.write_text(token, encoding="utf-8")
            output = run("--configure-provider", "bailian", "--token-file", str(secret_file), "--apply")
            self.assertNotIn(token, output)
            settings = json.loads((t3_home / "userdata/settings.json").read_text(encoding="utf-8"))
            route = settings["providerInstances"]["bailian"]
            self.assertTrue(route["enabled"])
            self.assertEqual(Path(route["config"]["homePath"]), t3_home / "userdata/provider-homes/bailian")
            profile = json.loads((Path(route["config"]["homePath"]) / "settings.json").read_text(encoding="utf-8"))
            self.assertEqual(profile["env"]["ANTHROPIC_AUTH_TOKEN"], token)
            output = run("--with-agent-rules", "--apply")
            self.assertNotIn("update:", output)
            self.assertNotIn(token, run("--doctor"))
            self.assertIn(str(home).replace("\\", "/"), (home / ".codex/AGENTS.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
