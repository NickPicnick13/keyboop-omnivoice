"""Per-user macOS LaunchAgent; never alters other Keyboop or OmniVoice services."""
import os
import plistlib
import platform
import subprocess
import sys
from pathlib import Path

LABEL = "dev.keyboop.omnivoice-kit"


def plist_path():
    return Path.home() / "Library" / "LaunchAgents" / (LABEL + ".plist")


def _launchctl(*args, check=True):
    return subprocess.run(["/bin/launchctl", *args], capture_output=True,
                          check=check, timeout=25)


def install_service(port=3912):
    if platform.system() != "Darwin" or not 1024 <= port <= 65535:
        raise ValueError("Service requires macOS and a valid user port")
    path = plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    log_dir = Path.home() / "Library" / "Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    env = {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
           "HF_HUB_DISABLE_TELEMETRY": "1", "TOKENIZERS_PARALLELISM": "false"}
    for key in ("KOV_MODEL_DIR", "KOV_DATA_DIR", "KOV_CONFIG_DIR", "KOV_STEPS", "KOV_SPEED"):
        if os.getenv(key):
            env[key] = os.environ[key]
    data = {
        "Label": LABEL,
        "ProgramArguments": [sys.executable, "-m", "keyboop_omnivoice.cli",
                             "serve", "--port", str(port)],
        "RunAtLoad": True,
        "KeepAlive": {"SuccessfulExit": False},
        "ThrottleInterval": 20,
        "EnvironmentVariables": env,
        "StandardOutPath": str(log_dir / "KeyboopOmniVoice.log"),
        "StandardErrorPath": str(log_dir / "KeyboopOmniVoice.log"),
        "ProcessType": "Background",
    }
    domain = "gui/" + str(os.getuid())
    if path.exists():
        _launchctl("bootout", domain, str(path), check=False)
    tmp = path.with_suffix(".plist.tmp")
    tmp.write_bytes(plistlib.dumps(data, fmt=plistlib.FMT_XML))
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    _launchctl("bootstrap", domain, str(path))
    _launchctl("enable", domain + "/" + LABEL)
    return path


def remove_service():
    path = plist_path()
    domain = "gui/" + str(os.getuid())
    if path.exists():
        _launchctl("bootout", domain, str(path), check=False)
        path.unlink()
    return path
