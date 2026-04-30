#!/usr/bin/env python3
import argparse
import os
import tarfile
import tempfile
import urllib.request
from pathlib import Path


PP_OCRV5_MOBILE_DET_URL = (
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/"
    "paddle3.0.0/PP-OCRv5_mobile_det_infer.tar"
)
PP_OCRV5_MOBILE_REC_URL = (
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/"
    "paddle3.0.0/PP-OCRv5_mobile_rec_infer.tar"
)


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)


def _find_infer_dir(root: Path) -> Path:
    """
    Try to find a directory containing Paddle inference artifacts.
    """
    candidates = []
    for p in root.rglob("inference.json"):
        candidates.append(p.parent)
    for p in root.rglob("inference.pdmodel"):
        candidates.append(p.parent)
    if candidates:
        return candidates[0]
    for p in root.rglob("model.json"):
        candidates.append(p.parent)
    for p in root.rglob("model.pdmodel"):
        candidates.append(p.parent)
    if candidates:
        return candidates[0]
    raise RuntimeError(f"Could not find inference model files under: {root}")


def ensure_model(url: str, models_dir: Path) -> Path:
    """
    Ensures model is downloaded+extracted and returns directory path that contains inference files.
    """
    models_dir.mkdir(parents=True, exist_ok=True)
    name = Path(url).name.replace(".tar", "")
    out_dir = models_dir / name

    # already extracted?
    if out_dir.exists():
        try:
            return _find_infer_dir(out_dir)
        except Exception:
            # fall through and re-extract
            pass

    with tempfile.TemporaryDirectory(prefix="paddleocr_model_") as td:
        td_path = Path(td)
        tar_path = td_path / "model.tar"
        _download(url, tar_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tar_path, "r:*") as tar:
            tar.extractall(path=out_dir)

    return _find_infer_dir(out_dir)


def main() -> int:
    ap = argparse.ArgumentParser(description="Download PaddleOCR inference models.")
    ap.add_argument("--models-dir", default=os.environ.get("PADDLEOCR_MODELS_DIR", "/models"))
    ap.add_argument(
        "--det-url",
        default=PP_OCRV5_MOBILE_DET_URL,
        help="Detection model tar URL",
    )
    ap.add_argument(
        "--rec-url",
        default=PP_OCRV5_MOBILE_REC_URL,
        help="Recognition model tar URL",
    )
    args = ap.parse_args()

    models_dir = Path(args.models_dir).resolve()
    det_dir = ensure_model(args.det_url, models_dir=models_dir)
    rec_dir = ensure_model(args.rec_url, models_dir=models_dir)
    print(f"DET_MODEL_DIR={det_dir}")
    print(f"REC_MODEL_DIR={rec_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

