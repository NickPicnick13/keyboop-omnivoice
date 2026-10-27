import argparse
import os
import platform
import sys
from pathlib import Path

from .config import add_clone, add_design, load_voices, remove_voice


def main():
    parser = argparse.ArgumentParser(prog="keyboop-omnivoice", description="Local OmniVoice TTS API for AI agents")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("list-voices")
    clone = sub.add_parser("add-voice")
    clone.add_argument("name")
    clone.add_argument("--file", required=True)
    clone.add_argument("--text", required=True)
    design = sub.add_parser("add-design")
    design.add_argument("name")
    design.add_argument("--instruction", required=True)
    remove = sub.add_parser("remove-voice")
    remove.add_argument("name")
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=int(os.getenv("KOV_PORT", "3912")))
    args = parser.parse_args()
    try:
        if args.command == "doctor":
            print("macOS:", platform.system(), "chip:", platform.machine(), "Python:", sys.version.split()[0])
            model = Path(os.getenv("KOV_MODEL_DIR", "")).expanduser()
            print("Model available:", bool(os.getenv("KOV_MODEL_DIR") and (model / "model.safetensors").exists()))
            try:
                import torch
                print("PyTorch MPS:", torch.backends.mps.is_available())
            except ImportError:
                print("PyTorch missing: install runtime extras")
            print("Voices:", ", ".join(sorted(load_voices())) or "none")
        elif args.command == "list-voices":
            for name, profile in sorted(load_voices().items()):
                print(name, profile.get("mode", "?"))
        elif args.command == "add-voice":
            add_clone(args.name, args.file, args.text)
            print("Added authorized voice:", args.name)
        elif args.command == "add-design":
            add_design(args.name, args.instruction)
            print("Added voice design:", args.name)
        elif args.command == "remove-voice":
            remove_voice(args.name)
            print("Removed:", args.name)
        elif args.command == "serve":
            if not 1024 <= args.port <= 65535:
                raise ValueError("Use a port between 1024 and 65535")
            import uvicorn
            uvicorn.run("keyboop_omnivoice.server:app", host="127.0.0.1", port=args.port, access_log=False)
    except (ValueError, RuntimeError) as exc:
        parser.exit(2, "Error: " + str(exc) + chr(10))


if __name__ == "__main__":
    main()
