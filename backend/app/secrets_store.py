import json
import os
import secrets
import csv
import subprocess
from pathlib import Path


def _restrict_directory(path: Path) -> None:
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"], capture_output=True, text=True, check=True, creationflags=flags)
        sid = next(csv.reader([result.stdout.strip()]))[1]
        subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r", f"*{sid}:(OI)(CI)F"], capture_output=True, check=True, creationflags=flags)
    else:
        os.chmod(path, 0o700)


def ensure_local_secrets(runtime_dir: Path) -> None:
    runtime_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    _restrict_directory(runtime_dir)
    path = runtime_dir / "local-secrets.json"
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        descriptor = None
    if descriptor is not None:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"session": secrets.token_hex(32), "identity_hmac": secrets.token_hex(32)}, handle)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if set(data) != {"session", "identity_hmac"} or any(len(bytes.fromhex(data[k])) != 32 for k in data) or data["session"] == data["identity_hmac"]:
            raise ValueError
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid local secret file") from exc
