#!/usr/bin/env python3
"""Preview or restore portable T3 settings without copying credentials."""

from __future__ import annotations

import argparse
import copy
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit


REPO = Path(__file__).absolute().parent.parent


class RestoreError(Exception):
    pass


@dataclass(frozen=True)
class Provider:
    id: str
    home: str
    secret_env: str


@dataclass
class Change:
    path: Path
    before: bytes | None
    after: bytes
    conflicts: list[str]

    @property
    def state(self) -> str:
        if self.before == self.after:
            return "unchanged"
        return "create" if self.before is None else "update"


def absolute(path: str | Path) -> Path:
    return Path(os.path.abspath(os.path.expanduser(str(path))))


def inside(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def plain_path(path: Path) -> None:
    """Reject links before resolving them, including Windows junctions."""
    for part in [path, *path.parents]:
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise RestoreError(f"Linked or reparse path refused: {part}")
        if part != path and not stat.S_ISDIR(info.st_mode):
            raise RestoreError(f"Parent is not a directory: {part}")


def read_bytes(path: Path) -> bytes | None:
    plain_path(path)
    if not path.exists():
        return None
    if not path.is_file():
        raise RestoreError(f"Expected a regular file: {path}")
    return path.read_bytes()


def read_json(path: Path, *, optional: bool = False, object_only: bool = True):
    raw = read_bytes(path)
    if raw is None:
        if optional:
            return {}, None
        raise RestoreError(f"Missing required file: {path}")
    try:
        value = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, ValueError):
        raise RestoreError(f"Invalid UTF-8 JSON: {path}") from None
    if object_only and not isinstance(value, dict):
        raise RestoreError(f"Expected a JSON object: {path}")
    return value, raw


def encode(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def render(value, home: Path, t3_home: Path):
    if isinstance(value, str):
        return value.replace("${USER_HOME}", home.as_posix()).replace(
            "${T3_HOME}", t3_home.as_posix()
        )
    if isinstance(value, dict):
        return {key: render(item, home, t3_home) for key, item in value.items()}
    if isinstance(value, list):
        return [render(item, home, t3_home) for item in value]
    return value


def merge(current, desired, key: str = ""):
    """Return the desired merge and differing managed paths, never values."""
    if isinstance(current, dict) and isinstance(desired, dict):
        result = copy.deepcopy(current)
        conflicts = []
        for name, value in desired.items():
            child = f"{key}.{name}" if key else name
            if name in current:
                result[name], found = merge(current[name], value, child)
                conflicts.extend(found)
            else:
                result[name] = copy.deepcopy(value)
        return result, conflicts
    if current == desired:
        return copy.deepcopy(current), []
    return copy.deepcopy(desired), [key or "<document>"]


def has_token(profile: dict, provider: Provider) -> bool:
    value = profile.get("env", {}).get(provider.secret_env)
    return isinstance(value, str) and bool(value.strip())


def alternate_auth(profile: dict) -> bool:
    env = profile.get("env", {})
    return bool(profile.get("apiKeyHelper") or env.get("ANTHROPIC_API_KEY")
                or env.get("ANTHROPIC_CUSTOM_HEADERS"))


def validate_endpoint(endpoint) -> None:
    if not isinstance(endpoint, str) or any(character.isspace() for character in endpoint):
        raise RestoreError("Provider template requires an HTTPS endpoint without credentials")
    try:
        parsed = urlsplit(endpoint)
        valid = (parsed.scheme == "https" and parsed.hostname and parsed.username is None
                 and parsed.password is None and not parsed.query and not parsed.fragment)
        parsed.port
    except ValueError:
        valid = False
    if not valid:
        raise RestoreError("Provider template requires an HTTPS endpoint without credentials")


class Restore:
    def __init__(self, repo: Path, home: Path, t3_home: Path):
        self.repo, self.home, self.t3_home = map(absolute, (repo, home, t3_home))
        plain_path(self.repo)
        plain_path(self.home)
        plain_path(self.t3_home)
        if inside(self.t3_home, self.repo) or inside(self.home, self.repo):
            raise RestoreError("Destination must be outside the repository checkout")
        self.templates = self.repo / "templates"
        self.userdata = self.t3_home / "userdata"
        self.manifest, _ = read_json(self.templates / "manifest.json")
        if self.manifest.get("schemaVersion") != 1:
            raise RestoreError("Unsupported template schemaVersion")
        entries = self.manifest.get("providers")
        if not isinstance(entries, dict) or not entries:
            raise RestoreError("Template providers must be a nonempty object")
        self.providers = {}
        used_homes = set()
        for provider_id, entry in entries.items():
            if (not isinstance(provider_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", provider_id)
                    or not isinstance(entry, dict)):
                raise RestoreError("Invalid provider registry entry")
            profile_home, secret_env = entry.get("home"), entry.get("secretEnv")
            if (not isinstance(profile_home, str)
                    or not re.fullmatch(r"[A-Za-z0-9_-]+", profile_home)
                    or profile_home in used_homes
                    or secret_env != "ANTHROPIC_AUTH_TOKEN"):
                raise RestoreError("Invalid provider home or secretEnv")
            used_homes.add(profile_home)
            self.providers[provider_id] = Provider(provider_id, profile_home, secret_env)

    def template(self, relative: str, *, object_only: bool = True):
        value, _ = read_json(self.templates / relative, object_only=object_only)
        return render(value, self.home, self.t3_home)

    def profile_path(self, provider: Provider) -> Path:
        return self.userdata / "provider-homes" / provider.home / "settings.json"

    def checked_profile(self, provider: Provider):
        desired = self.template(f"t3/provider-homes/{provider.home}/settings.json")
        if (not isinstance(desired.get("env"), dict) or provider.secret_env in desired["env"]
                or alternate_auth(desired)):
            raise RestoreError("Provider template must contain env without credentials")
        endpoint = desired["env"].get("ANTHROPIC_BASE_URL")
        validate_endpoint(endpoint)
        current, raw = read_json(self.profile_path(provider), optional=True)
        if "env" in current and not isinstance(current["env"], dict):
            raise RestoreError(f"Invalid provider env object: {provider.id}")
        if ((has_token(current, provider) or alternate_auth(current))
                and current.get("env", {}).get("ANTHROPIC_BASE_URL") != endpoint):
            raise RestoreError(f"Credential endpoint mismatch refused: {provider.id}")
        return current, desired, raw

    def json_change(self, path: Path, desired, *, object_only: bool = True) -> Change:
        if inside(path, self.repo):
            raise RestoreError("Refusing to write inside the repository checkout")
        current, raw = read_json(path, optional=True, object_only=object_only)
        if raw is None:
            return Change(path, None, encode(desired), [])
        merged, conflicts = merge(current, desired)
        return Change(path, raw, raw if current == merged else encode(merged), conflicts)

    def plan(self, with_agent_rules: bool = False) -> list[Change]:
        settings = self.template("t3/settings.json")
        instances = settings.get("providerInstances")
        if not isinstance(instances, dict):
            raise RestoreError("Template settings require providerInstances")
        changes = []
        existing_settings, _ = read_json(self.userdata / "settings.json", optional=True)
        existing_instances = existing_settings.get("providerInstances", {})
        if not isinstance(existing_instances, dict):
            raise RestoreError("Invalid installed providerInstances object")
        for provider in self.providers.values():
            current, desired, _ = self.checked_profile(provider)
            instance = instances.get(provider.id)
            if not isinstance(instance, dict) or instance.get("driver") != "claudeAgent":
                raise RestoreError(f"Invalid template driver: {provider.id}")
            expected_home = (self.profile_path(provider).parent).as_posix()
            if instance.get("config", {}).get("homePath") != expected_home:
                raise RestoreError(f"Invalid template homePath: {provider.id}")
            existing = existing_instances.get(provider.id, {})
            previous_enabled = existing.get("enabled") if isinstance(existing, dict) else None
            instance["enabled"] = has_token(current, provider) and previous_enabled is not False
            changes.append(self.json_change(self.profile_path(provider), desired))
        changes.extend([
            self.json_change(self.userdata / "settings.json", settings),
            self.json_change(self.userdata / "client-settings.json", self.template("t3/client-settings.json")),
            self.json_change(self.userdata / "keybindings.json", self.template("t3/keybindings.json", object_only=False), object_only=False),
        ])
        if with_agent_rules:
            agent_files = {
                "AGENTS.md": self.home / ".codex" / "AGENTS.md",
                "pstack-models.md": self.home / ".agents" / "pstack-models.md",
                "pstack-auto/SKILL.md": self.home / ".agents" / "skills" / "pstack-auto" / "SKILL.md",
            }
            for relative, destination in agent_files.items():
                source = self.templates / "agent" / relative
                raw = read_bytes(source)
                if raw is None:
                    raise RestoreError(f"Missing required file: {source}")
                try:
                    desired = render(raw.decode("utf-8-sig"), self.home, self.t3_home).encode("utf-8")
                except UnicodeError:
                    raise RestoreError(f"Invalid UTF-8 template: {source}") from None
                before = read_bytes(destination)
                if before is not None:
                    try:
                        same_text = (before.decode("utf-8-sig").replace("\r\n", "\n")
                                     == desired.decode("utf-8-sig").replace("\r\n", "\n"))
                    except UnicodeError:
                        same_text = False
                    if same_text:
                        desired = before
                changes.append(Change(destination, before, desired,
                                      ["<document>"] if before is not None and before != desired else []))
        return changes

    def auth_plan(self, provider_id: str, token: str, overwrite: bool) -> list[Change]:
        if provider_id not in self.providers:
            raise RestoreError("Unknown provider ID")
        provider = self.providers[provider_id]
        current, desired, raw = self.checked_profile(provider)
        settings_path = self.userdata / "settings.json"
        settings, settings_raw = read_json(settings_path)
        instances = settings.get("providerInstances", {})
        if not isinstance(instances, dict):
            raise RestoreError("Invalid installed providerInstances object")
        instance = instances.get(provider_id)
        config = instance.get("config") if isinstance(instance, dict) else None
        configured_home = config.get("homePath") if isinstance(config, dict) else None
        expected_home = self.profile_path(provider).parent
        if (raw is None or not isinstance(instance, dict)
                or instance.get("driver") != "claudeAgent"
                or not isinstance(configured_home, str) or not Path(configured_home).is_absolute()
                or absolute(configured_home) != expected_home
                or current.get("env", {}).get("ANTHROPIC_BASE_URL") != desired["env"]["ANTHROPIC_BASE_URL"]):
            raise RestoreError("Provider is not initialized with the trusted template; restore it first")
        if alternate_auth(current):
            raise RestoreError("Alternate API key, headers or apiKeyHelper present; reconcile authentication before configuring this provider")
        if has_token(current, provider) and current["env"][provider.secret_env] != token and not overwrite:
            raise RestoreError("Provider already has a credential; replacing it requires --overwrite")
        if not token or any(character.isspace() for character in token):
            raise RestoreError("Credential must be a nonempty single-line value without whitespace")
        profile = copy.deepcopy(current)
        profile["env"][provider.secret_env] = token
        enabled = copy.deepcopy(settings)
        enabled["providerInstances"][provider_id]["enabled"] = True
        return [
            Change(self.profile_path(provider), raw, raw if profile == current else encode(profile), []),
            Change(settings_path, settings_raw, settings_raw if enabled == settings else encode(enabled), []),
        ]


def t3_is_running() -> bool:
    try:
        if os.name == "nt":
            result = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, timeout=10)
            if result.returncode:
                raise RestoreError("Could not inspect running apps; close T3 and check tasklist")
            return any(line.lstrip().lower().startswith(b'"t3 code') for line in result.stdout.splitlines())
        proc = Path("/proc")
        if proc.is_dir():
            for item in proc.iterdir():
                if item.name.isdigit():
                    try:
                        command = (item / "comm").read_text().strip().lower()
                    except (OSError, UnicodeError):
                        continue
                    if command.startswith("t3 code") or command == "t3code":
                        return True
            return False
        result = subprocess.run(["pgrep", "-x", "T3 Code|T3 Code \\(Nightly\\)|t3code"], capture_output=True, timeout=10)
        if result.returncode not in (0, 1):
            raise RestoreError("Could not inspect running apps; close T3 and check pgrep")
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        raise RestoreError("Could not inspect running apps; close T3 before applying") from None


def ensure_app_closed(restore: Restore) -> None:
    real_home = absolute(Path.home())
    real_t3 = absolute(os.environ.get("T3CODE_HOME", real_home / ".t3"))
    if (restore.home == real_home or restore.t3_home == real_t3) and t3_is_running():
        raise RestoreError("T3 is running. Close T3 and run this command from an external terminal")


def apply_changes(changes: list[Change], *, overwrite: bool) -> None:
    if any(change.conflicts for change in changes) and not overwrite:
        raise RestoreError("Conflicts found; no files written. Merge them before using --overwrite")
    for change in changes:
        if read_bytes(change.path) != change.before:
            raise RestoreError(f"File changed since preview; no write started: {change.path}")
    for change in changes:
        if change.state == "unchanged":
            continue
        plain_path(change.path)
        change.path.parent.mkdir(parents=True, exist_ok=True)
        if read_bytes(change.path) != change.before:
            raise RestoreError(f"File changed during apply; inspect prior writes and backups: {change.path}")
        if change.before is not None:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup = change.path.with_name(f"{change.path.name}.bak-{stamp}")
            plain_path(backup)
            descriptor = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(change.before)
                stream.flush()
                os.fsync(stream.fileno())
        descriptor, temporary = tempfile.mkstemp(prefix=f".{change.path.name}.", suffix=".tmp", dir=change.path.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(change.after)
                stream.flush()
                os.fsync(stream.fileno())
            plain_path(change.path)
            if read_bytes(change.path) != change.before:
                raise RestoreError(f"File changed during apply; inspect prior writes and backups: {change.path}")
            os.replace(temporary, change.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def doctor(restore: Restore) -> None:
    print(f"T3 home: {restore.t3_home}")
    source = restore.manifest.get("source", {})
    expected_version = source.get("t3Version", "not recorded")
    version_file = restore.userdata / "desktop-last-started-version"
    raw = read_bytes(version_file)
    actual = raw.decode("utf-8-sig").strip() if raw else None
    print(f"Source T3 version: {expected_version}")
    print(f"Installed T3 version: {actual or 'not detected'}")
    print("Version compatibility: " + ("same snapshot" if actual == expected_version else "unverified"))
    settings, _ = read_json(restore.userdata / "settings.json", optional=True)
    for provider in restore.providers.values():
        profile, _, _ = restore.checked_profile(provider)
        instance = settings.get("providerInstances", {}).get(provider.id, {})
        print(f"Provider {provider.id}: enabled={instance.get('enabled') is True}, credential={'present' if has_token(profile, provider) else 'missing'}")
    names = {"Git": "git", "Codex": "codex", "Claude Code": "claude", "T3 CLI": "t3", "Ego": "ego-browser", "Cua Driver": "cua-driver"}
    windows = {
        "Ego": restore.home / ".local/share/ego/active_version_dir/ego-browser.exe",
        "Cua Driver": restore.home / "AppData/Local/Programs/Cua/cua-driver/bin/cua-driver.exe",
        "T3 CLI": restore.t3_home / "bin/t3.cmd",
    }
    print(f"Python: {sys.executable}")
    for label, command in names.items():
        found = shutil.which(command)
        if not found and label in windows and windows[label].is_file():
            found = str(windows[label])
        print(f"{label}: {found or 'not detected'}")
    print("Read-only inspection only. Login, API entitlement, model calls and GUI behavior are unverified.")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--home", type=Path, default=Path.home(), help="Target user home (default: actual user home)")
    result.add_argument("--t3-home", type=Path, help="Target T3CODE_HOME (default: environment or HOME/.t3)")
    result.add_argument("--apply", action="store_true", help="Write the previewed changes")
    result.add_argument("--with-agent-rules", action="store_true", help="Also restore Codex rules and pstack preferences")
    result.add_argument("--overwrite", action="store_true", help="Replace conflicting managed values after making backups")
    result.add_argument("--doctor", action="store_true", help="Inspect local files and tools without changing them")
    result.add_argument("--configure-provider", metavar="ID", help="Privately supply a key and enable an initialized provider")
    result.add_argument("--token-file", type=Path, help="Read the key from a private file outside this checkout")
    return result


def main(argv: list[str] | None = None, *, repo: Path = REPO) -> int:
    args = parser().parse_args(argv)
    try:
        if args.doctor and (args.apply or args.configure_provider or args.token_file):
            raise RestoreError("--doctor cannot be combined with write or credential options")
        if args.token_file and not args.configure_provider:
            raise RestoreError("--token-file requires --configure-provider")
        if args.configure_provider and args.with_agent_rules:
            raise RestoreError("Configure credentials separately from --with-agent-rules")
        target_t3 = args.t3_home or os.environ.get("T3CODE_HOME") or args.home / ".t3"
        restore = Restore(repo, args.home, Path(target_t3))
        if args.doctor:
            doctor(restore)
            return 0
        if args.configure_provider:
            if args.configure_provider not in restore.providers:
                raise RestoreError("Unknown provider ID")
            if not args.apply:
                print(f"Credential preview: {args.configure_provider}; add --apply to enter its key privately")
                return 0
            ensure_app_closed(restore)
            if args.token_file:
                token_path = absolute(args.token_file)
                if inside(token_path, restore.repo):
                    raise RestoreError("Credential input must be outside the repository checkout")
                raw = read_bytes(token_path)
                if raw is None:
                    raise RestoreError("Credential input file does not exist")
                token = raw.decode("utf-8-sig").strip()
            else:
                if not sys.stdin.isatty():
                    raise RestoreError("No interactive terminal; use a private --token-file outside the checkout")
                token = getpass.getpass("API key (hidden): ").strip()
            changes = restore.auth_plan(args.configure_provider, token, args.overwrite)
        else:
            changes = restore.plan(args.with_agent_rules)
        for change in changes:
            print(f"{change.state}: {change.path}")
            for key in change.conflicts:
                print(f"  conflict: {key}")
        if args.apply:
            ensure_app_closed(restore)
            apply_changes(changes, overwrite=args.overwrite)
            print("Applied. Changed existing files have adjacent .bak-* backups. No network or model calls ran.")
        else:
            print("Preview only. No files written. Add --apply after reviewing the plan.")
        return 0
    except RestoreError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError, TypeError, AttributeError, KeyError):
        print("Error: Could not read or write the configuration. No credential values are shown; inspect paths and file structure.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
