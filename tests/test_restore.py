import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("y3_restore", ROOT / "scripts/restore.py")
restore = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = restore
SPEC.loader.exec_module(restore)
TOKEN = "fixture-not-a-real-api-key"


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.home = self.root / "new-user"
        self.t3 = self.home / ".t3"
        self.userdata = self.t3 / "userdata"
        self.write(self.repo / "templates/manifest.json", {
            "schemaVersion": 1,
            "source": {"t3Version": "test-version"},
            "providers": {"relay": {"home": "relay-home", "secretEnv": "ANTHROPIC_AUTH_TOKEN"}},
        })
        self.write(self.repo / "templates/t3/settings.json", {
            "providerInstances": {
                "codex": {"driver": "codex", "enabled": True, "config": {"setupMode": "existing"}},
                "relay": {"driver": "claudeAgent", "enabled": False, "config": {
                    "homePath": "${T3_HOME}/userdata/provider-homes/relay-home",
                    "customModels": ["test-model"],
                }},
            },
            "defaultModelSelection": {"instanceId": "codex", "model": "test-model"},
        })
        self.write(self.repo / "templates/t3/client-settings.json", {"fontSizeInterface": 16})
        self.write(self.repo / "templates/t3/keybindings.json", [{"key": "mod+n", "command": "chat.new"}])
        self.write(self.repo / "templates/t3/provider-homes/relay-home/settings.json", {
            "env": {"ANTHROPIC_BASE_URL": "https://provider.example", "ANTHROPIC_MODEL": "test-model"},
        })
        for name in ("AGENTS.md", "pstack-models.md", "pstack-auto/SKILL.md"):
            path = self.repo / "templates/agent" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("rules at ${USER_HOME}\n", encoding="utf-8")
        (self.repo / "scripts").mkdir()
        shutil.copyfile(ROOT / "scripts/restore.py", self.repo / "scripts/restore.py")

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def read(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def engine(self):
        return restore.Restore(self.repo, self.home, self.t3)

    def run_main(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = restore.main(["--home", str(self.home), "--t3-home", str(self.t3), *args], repo=self.repo)
        return code, stdout.getvalue() + stderr.getvalue()

    def apply(self, **options):
        restore.apply_changes(self.engine().plan(**options), overwrite=False)

    def tree(self):
        return {path.relative_to(self.home).as_posix(): path.read_bytes()
                for path in self.home.rglob("*") if path.is_file()} if self.home.exists() else {}

    def profile_path(self):
        return self.userdata / "provider-homes/relay-home/settings.json"

    def inject(self, token=TOKEN, overwrite=False):
        changes = self.engine().auth_plan("relay", token, overwrite)
        restore.apply_changes(changes, overwrite=overwrite)

    def test_preview_and_doctor_do_not_create_target(self):
        for args in ((), ("--doctor",), ("--configure-provider", "relay")):
            with self.subTest(args=args):
                code, output = self.run_main(*args)
                self.assertEqual(code, 0, output)
                self.assertFalse(self.home.exists())

    def test_apply_expands_paths_and_rerun_preserves_bytes(self):
        self.apply(with_agent_rules=True)
        settings = self.read(self.userdata / "settings.json")
        self.assertEqual(settings["providerInstances"]["relay"]["config"]["homePath"],
                         (self.userdata / "provider-homes/relay-home").as_posix())
        self.assertFalse(settings["providerInstances"]["relay"]["enabled"])
        self.assertIn(self.home.as_posix(), (self.home / ".codex/AGENTS.md").read_text())
        before = self.tree()
        self.apply(with_agent_rules=True)
        self.assertEqual(before, self.tree())
        self.assertFalse(list(self.home.rglob("*.bak-*")))

    def test_merge_preserves_unrelated_provider_environment_and_token(self):
        self.apply()
        profile = self.read(self.profile_path())
        profile["env"].update({"ANTHROPIC_AUTH_TOKEN": TOKEN, "KEEP_ME": "existing"})
        profile["permissions"] = {"allow": ["Read"]}
        self.write(self.profile_path(), profile)
        settings = self.read(self.userdata / "settings.json")
        settings["unrelated"] = {"value": True}
        settings["providerInstances"]["other"] = {"driver": "codex"}
        settings["providerInstances"]["relay"]["enabled"] = True
        self.write(self.userdata / "settings.json", settings)
        self.apply()
        result = self.read(self.profile_path())
        self.assertEqual(profile, result)
        self.assertEqual(settings, self.read(self.userdata / "settings.json"))

    def test_equivalent_windows_rule_text_keeps_original_bytes(self):
        self.apply(with_agent_rules=True)
        path = self.home / ".codex/AGENTS.md"
        original = b"\xef\xbb\xbf" + path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        path.write_bytes(original)
        before = self.tree()
        self.apply(with_agent_rules=True)
        self.assertEqual(before, self.tree())

    def test_intentionally_disabled_provider_stays_disabled(self):
        self.apply()
        profile = self.read(self.profile_path())
        profile["env"]["ANTHROPIC_AUTH_TOKEN"] = TOKEN
        self.write(self.profile_path(), profile)
        self.apply()
        self.assertFalse(self.read(self.userdata / "settings.json")["providerInstances"]["relay"]["enabled"])

    def test_conflict_preflight_refuses_every_write_and_hides_values(self):
        self.write(self.userdata / "client-settings.json", {"fontSizeInterface": 99, "private": TOKEN})
        before = self.tree()
        code, output = self.run_main("--apply")
        self.assertEqual(code, 1)
        self.assertIn("fontSizeInterface", output)
        self.assertNotIn(TOKEN, output)
        self.assertEqual(before, self.tree())

    def test_overwrite_backs_up_original_exactly(self):
        path = self.userdata / "client-settings.json"
        self.write(path, {"fontSizeInterface": 99, "private": "keep"})
        before = path.read_bytes()
        code, output = self.run_main("--apply", "--overwrite")
        self.assertEqual(code, 0, output)
        self.assertEqual(self.read(path), {"fontSizeInterface": 16, "private": "keep"})
        backups = list(path.parent.glob("client-settings.json.bak-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), before)

    def test_auth_injects_key_without_output_and_survives_restore(self):
        self.apply()
        token_file = self.root / "private-input"
        token_file.write_text(TOKEN, encoding="utf-8")
        code, output = self.run_main("--apply", "--configure-provider", "relay", "--token-file", str(token_file))
        self.assertEqual(code, 0, output)
        self.assertNotIn(TOKEN, output)
        self.assertEqual(self.read(self.profile_path())["env"]["ANTHROPIC_AUTH_TOKEN"], TOKEN)
        self.assertTrue(self.read(self.userdata / "settings.json")["providerInstances"]["relay"]["enabled"])
        before = self.tree()
        self.apply()
        self.assertEqual(before, self.tree())
        code, output = self.run_main("--doctor")
        self.assertEqual(code, 0, output)
        self.assertIn("credential=present", output)
        self.assertNotIn(TOKEN, output)

    def test_auth_refuses_uninitialized_or_changed_routes(self):
        with self.assertRaises(restore.RestoreError):
            self.engine().auth_plan("relay", TOKEN, False)
        self.apply()
        settings = self.read(self.userdata / "settings.json")
        settings["providerInstances"]["relay"]["driver"] = "wrong"
        self.write(self.userdata / "settings.json", settings)
        before = self.tree()
        with self.assertRaises(restore.RestoreError):
            self.engine().auth_plan("relay", TOKEN, True)
        self.assertEqual(before, self.tree())

    def test_existing_key_replacement_requires_overwrite(self):
        self.apply()
        self.inject()
        before = self.tree()
        with self.assertRaises(restore.RestoreError):
            self.inject("another-fixture-key")
        self.assertEqual(before, self.tree())
        self.inject("another-fixture-key", overwrite=True)
        self.assertEqual(self.read(self.profile_path())["env"]["ANTHROPIC_AUTH_TOKEN"], "another-fixture-key")

    def test_wrong_endpoint_credential_is_never_reused_even_with_overwrite(self):
        self.apply()
        self.write(self.profile_path(), {"env": {
            "ANTHROPIC_BASE_URL": "https://different.example", "ANTHROPIC_AUTH_TOKEN": TOKEN,
        }})
        before = self.tree()
        code, output = self.run_main("--apply", "--overwrite")
        self.assertEqual(code, 1)
        self.assertIn("Credential endpoint mismatch", output)
        self.assertNotIn(TOKEN, output)
        self.assertEqual(before, self.tree())

    def test_legacy_key_and_helper_refuse_endpoint_change_and_token_injection(self):
        self.apply()
        for alternate in ({"env": {"ANTHROPIC_API_KEY": TOKEN}},
                          {"apiKeyHelper": "local-auth-helper"},
                          {"env": {"ANTHROPIC_CUSTOM_HEADERS": "Authorization: fixture"}}):
            with self.subTest(alternate=list(alternate)):
                profile = {"env": {"ANTHROPIC_BASE_URL": "https://provider.example"}}
                profile["env"].update(alternate.get("env", {}))
                if "apiKeyHelper" in alternate:
                    profile["apiKeyHelper"] = alternate["apiKeyHelper"]
                self.write(self.profile_path(), profile)
                with self.assertRaisesRegex(restore.RestoreError, "Alternate API key"):
                    self.engine().auth_plan("relay", "new-fixture-token", True)
                profile["env"]["ANTHROPIC_BASE_URL"] = "https://different.example"
                self.write(self.profile_path(), profile)
                before = self.tree()
                code, output = self.run_main("--apply", "--overwrite")
                self.assertEqual(code, 1)
                self.assertIn("Credential endpoint mismatch", output)
                self.assertNotIn(TOKEN, output)
                self.assertEqual(before, self.tree())

    def test_credential_bearing_or_invalid_template_endpoint_refused(self):
        path = self.repo / "templates/t3/provider-homes/relay-home/settings.json"
        for endpoint in ("https://user:fixture@provider.example", "https://provider.example?key=fixture",
                         "https://provider.example#fixture", "https://", "http://provider.example",
                         "https://provider.example:bad", "https://provider.example/\n"):
            with self.subTest(endpoint=endpoint):
                self.write(path, {"env": {"ANTHROPIC_BASE_URL": endpoint}})
                code, output = self.run_main("--apply")
                self.assertEqual(code, 1)
                self.assertNotIn(endpoint, output)
                self.assertFalse(self.home.exists())

    def test_symlink_and_junction_destination_refused(self):
        destination = self.root / "outside"
        destination.mkdir()
        self.home.mkdir()
        link = self.home / ".t3"
        try:
            link.symlink_to(destination, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                self.skipTest("Symlink creation unavailable")
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(destination)], capture_output=True)
            self.assertEqual(result.returncode, 0, "Could not create a test junction")
        self.addCleanup(lambda: link.rmdir() if os.name == "nt" and link.exists() and not link.is_symlink() else link.unlink(missing_ok=True))
        code, output = self.run_main("--apply", "--overwrite")
        self.assertEqual(code, 1)
        self.assertIn("Linked or reparse", output)
        self.assertEqual(list(destination.iterdir()), [])

    def test_repository_destination_and_credential_input_refused(self):
        with self.assertRaises(restore.RestoreError):
            restore.Restore(self.repo, self.home, self.repo / "local")
        self.apply()
        token_file = self.repo / "private-input"
        token_file.write_text(TOKEN, encoding="utf-8")
        before = self.tree()
        code, output = self.run_main("--apply", "--configure-provider", "relay", "--token-file", str(token_file))
        self.assertEqual(code, 1)
        self.assertNotIn(TOKEN, output)
        self.assertEqual(before, self.tree())

    def test_invalid_json_fails_closed_without_echoing_input(self):
        path = self.userdata / "keybindings.json"
        path.parent.mkdir(parents=True)
        path.write_text("invalid " + TOKEN)
        before = self.tree()
        code, output = self.run_main("--apply", "--overwrite")
        self.assertEqual(code, 1)
        self.assertIn("Invalid UTF-8 JSON", output)
        self.assertNotIn(TOKEN, output)
        self.assertEqual(before, self.tree())

    def test_manifest_path_traversal_refused(self):
        path = self.repo / "templates/manifest.json"
        manifest = self.read(path)
        manifest["providers"]["relay"]["home"] = "../outside"
        self.write(path, manifest)
        code, output = self.run_main("--apply")
        self.assertEqual(code, 1)
        self.assertFalse(self.home.exists())

    def test_changed_file_after_plan_is_not_overwritten(self):
        changes = self.engine().plan()
        self.write(self.userdata / "client-settings.json", {"newer": True})
        before = self.tree()
        with self.assertRaises(restore.RestoreError):
            restore.apply_changes(changes, overwrite=True)
        self.assertEqual(before, self.tree())

    def test_real_running_t3_guard_and_isolated_target(self):
        with patch.object(restore, "t3_is_running", return_value=True):
            restore.ensure_app_closed(self.engine())
            with patch.object(restore.Path, "home", return_value=self.home):
                with self.assertRaises(restore.RestoreError):
                    restore.ensure_app_closed(self.engine())

    def test_cli_apply_and_second_preview(self):
        command = [sys.executable, str(self.repo / "scripts/restore.py"), "--home", str(self.home), "--t3-home", str(self.t3)]
        first = subprocess.run([*command, "--apply", "--with-agent-rules"], capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        before = self.tree()
        second = subprocess.run([*command, "--with-agent-rules"], capture_output=True, text=True)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn("unchanged:", second.stdout)
        self.assertNotIn("update:", second.stdout)
        self.assertEqual(before, self.tree())


if __name__ == "__main__":
    unittest.main()
