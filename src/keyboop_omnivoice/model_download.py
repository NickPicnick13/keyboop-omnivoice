"""Explicit user-authorized download of upstream noncommercial pretrained weights."""
import os

from .config import model_dir, model_is_ready

MODEL_REPO = "k2-fsa/OmniVoice"
PATTERNS = [
    "config.json", "model.safetensors", "tokenizer.json",
    "tokenizer_config.json", "chat_template.jinja",
    "README.md", "audio_tokenizer/*",
]


def download_model(accept_license=False):
    if not accept_license:
        raise ValueError("The pretrained weights are CC-BY-NC. Pass --accept-noncommercial-license to confirm.")
    if model_is_ready():
        return model_dir()
    target = model_dir()
    target.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(target, 0o700)
    from huggingface_hub import snapshot_download
    snapshot_download(
        repo_id=MODEL_REPO,
        local_dir=str(target),
        allow_patterns=PATTERNS,
        max_workers=4,
    )
    if not model_is_ready():
        raise RuntimeError("Incomplete model download; rerun the download command to resume.")
    return target
