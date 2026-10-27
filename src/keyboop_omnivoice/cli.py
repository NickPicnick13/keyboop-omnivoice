"""CLI and one-time initialization for the installable local suite."""
import argparse
import os
import platform
import sys
import webbrowser
from pathlib import Path

from .config import add_clone, add_design, load_voices, model_dir, model_is_ready, remove_voice


def doctor():
    print("Platform:", platform.system(), platform.machine(), platform.mac_ver()[0])
    print("Python:", sys.version.split()[0])
    print("Model:", "ready" if model_is_ready() else "missing")
    print("Model directory:", model_dir())
    try:
        import torch
        print("MPS acceleration:", "available" if torch.backends.mps.is_available() else "unavailable")
    except ImportError:
        print("PyTorch: not installed; run Install.command")
    try:
        from .keyboop_install import installed_path
        print("Keyboop:", installed_path() or "not installed")
    except Exception:
        print("Keyboop: status unknown")
    print("Saved voice profiles:", ", ".join(sorted(load_voices())) or "none")


def main():
    parser = argparse.ArgumentParser(prog="keyboop-omnivoice", description="Local Keyboop + OmniVoice suite")
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("doctor")
    subs.add_parser("list-voices")
    add_voice = subs.add_parser("add-voice", help="Clone a voice with explicit consent")
    add_voice.add_argument("name")
    add_voice.add_argument("--file", required=True)
    add_voice.add_argument("--text", required=True)
    design = subs.add_parser("add-design", help="Design a voice without audio")
    design.add_argument("name")
    design.add_argument("--instruction", required=True)
    design.add_argument("--language", default="Russian", choices=("Russian", "English"))
    remove = subs.add_parser("remove-voice")
    remove.add_argument("name")
    download = subs.add_parser("download-model")
    download.add_argument("--accept-noncommercial-license", action="store_true")
    subs.add_parser("install-keyboop")
    subs.add_parser("bootstrap")
    serve = subs.add_parser("serve")
    serve.add_argument("--port", type=int, default=int(os.environ.get("KOV_PORT", "3912")))
    open_ui = subs.add_parser("open-ui")
    open_ui.add_argument("--port", type=int, default=int(os.environ.get("KOV_PORT", "3912")))
    service = subs.add_parser("service")
    service.add_argument("action", choices=("install", "remove"))
    service.add_argument("--port", type=int, default=3912)
    args = parser.parse_args()
    try:
        if args.command == "doctor":
            doctor()
        elif args.command == "list-voices":
            for name, profile in sorted(load_voices().items()):
                print(name, profile.get("mode", "?"))
        elif args.command == "add-voice":
            add_clone(args.name, args.file, args.text)
            print("Added consented voice:", args.name)
        elif args.command == "add-design":
            add_design(args.name, args.instruction, args.language)
            print("Added voice:", args.name)
        elif args.command == "remove-voice":
            remove_voice(args.name)
            print("Removed:", args.name)
        elif args.command == "download-model":
            from .model_download import download_model
            print("Model ready:", download_model(args.accept_noncommercial_license))
        elif args.command == "install-keyboop":
            from .keyboop_install import install_keyboop
            print("Official Keyboop:", install_keyboop())
        elif args.command == "bootstrap":
            if not load_voices():
                add_design("narrator", "female, moderate pitch, russian accent", "Russian")
                print("Default 'narrator' voice created")
            else:
                print("Preserved existing voice profiles")
        elif args.command == "serve":
            if not 1024 <= args.port <= 65535:
                raise ValueError("Choose a port between 1024 and 65535")
            import uvicorn
            uvicorn.run("keyboop_omnivoice.server:app", host="127.0.0.1",
                        port=args.port, access_log=False)
        elif args.command == "open-ui":
            webbrowser.open("http://127.0.0.1:" + str(args.port) + "/")
        elif args.command == "service":
            from .services import install_service, remove_service
            if args.action == "install":
                print("Autostart installed:", install_service(args.port))
            else:
                print("Autostart removed:", remove_service())
    except (ValueError, RuntimeError) as exc:
        parser.exit(2, "Error: " + str(exc) + chr(10))


if __name__ == "__main__":
    main()
