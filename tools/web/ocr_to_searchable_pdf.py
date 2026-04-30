#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


def _require_module(name: str, pip_hint: str) -> None:
    try:
        __import__(name)
    except Exception as e:
        raise SystemExit(
            f"Missing Python dependency '{name}'.\n"
            f"Install it, e.g.:\n\n  {pip_hint}\n\n"
            f"Original error: {e}"
        )


_require_module("fitz", "python3 -m pip install PyMuPDF")
_require_module("PIL", "python3 -m pip install Pillow")

import fitz  # type: ignore  # noqa: E402
from PIL import Image  # type: ignore  # noqa: E402


@dataclass(frozen=True)
class OcrLine:
    text: str
    points: list[list[float]]  # [[x,y],...]

def _ensure_models(repo_root: Path, models_dir: Path) -> tuple[Path, Path]:
    """
    Uses `tools/web/download_ocr_models.py` to download OCR det+rec models
    into `models_dir` and returns (det_dir, rec_dir).
    """
    dl = repo_root / "tools" / "web" / "download_ocr_models.py"
    if not dl.exists():
        raise RuntimeError(f"Missing downloader script: {dl}")
    proc = subprocess.run(
        [sys.executable, str(dl), "--models-dir", str(models_dir)],
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Model download failed:\n{proc.stdout}")
    det, rec = None, None
    for line in proc.stdout.splitlines():
        if line.startswith("DET_MODEL_DIR="):
            det = Path(line.split("=", 1)[1].strip())
        if line.startswith("REC_MODEL_DIR="):
            rec = Path(line.split("=", 1)[1].strip())
    if not det or not rec:
        raise RuntimeError(f"Could not parse model dirs from downloader output:\n{proc.stdout}")
    return det, rec


def _run_predict_system(
    repo_root: Path,
    image_path: Path,
    work_dir: Path,
    extra_args: list[str],
) -> list[OcrLine]:
    """
    Runs PaddleOCR's `tools/infer/predict_system.py` on a single image.
    Expects it to write `<work_dir>/system_results.txt`.
    """
    draw_dir = work_dir / "predict_out"
    draw_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(repo_root / "tools" / "infer" / "predict_system.py"),
        "--image_dir",
        str(image_path),
        "--draw_img_save_dir",
        str(draw_dir),
        "--show_log",
        "false",
    ] + extra_args

    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"predict_system.py failed:\n{proc.stdout}")

    results_path = draw_dir / "system_results.txt"
    if not results_path.exists():
        raise RuntimeError(
            f"predict_system.py did not produce {results_path}. Output:\n{proc.stdout}"
        )

    # Format: "<basename>\t<json>\n"
    lines: list[OcrLine] = []
    for raw in results_path.read_text(encoding="utf-8").splitlines():
        if "\t" not in raw:
            continue
        _, payload = raw.split("\t", 1)
        try:
            arr = json.loads(payload)
        except Exception:
            continue
        for item in arr:
            t = (item.get("transcription") or "").strip()
            pts = item.get("points")
            if not t or not isinstance(pts, list) or len(pts) < 4:
                continue
            lines.append(OcrLine(text=t, points=pts))
    return lines


def _bbox_from_points(points: list[list[float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _image_size_px(path: Path) -> tuple[int, int]:
    with Image.open(path) as im:
        return int(im.size[0]), int(im.size[1])


def _convert_input_to_images(input_path: Path, work_dir: Path, dpi: int) -> list[Path]:
    """
    If input is a PDF, renders pages to PNG images at `dpi`.
    If input is an image, just copies it into the work dir.
    Returns a list of image file paths in page order.
    """
    ext = input_path.suffix.lower()
    out_dir = work_dir / "pages"
    out_dir.mkdir(parents=True, exist_ok=True)

    if ext == ".pdf":
        doc = fitz.open(str(input_path))
        image_paths: list[Path] = []
        try:
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            for i in range(doc.page_count):
                page = doc.load_page(i)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                out = out_dir / f"page_{i+1:04d}.png"
                pix.save(str(out))
                image_paths.append(out)
        finally:
            doc.close()
        return image_paths

    # treat everything else as image
    out = out_dir / f"page_0001{ext if ext else '.png'}"
    shutil.copyfile(str(input_path), str(out))
    return [out]


def _insert_invisible_text(page: fitz.Page, rect: fitz.Rect, text: str) -> None:
    # Render mode 3 == invisible text (kept for search/select).
    height = max(1.0, rect.height)
    fontsize = max(4.0, height * 0.8)
    page.insert_textbox(
        rect,
        text,
        fontsize=fontsize,
        fontname="helv",
        render_mode=3,
        align=0,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate searchable PDF using PaddleOCR + invisible text layer."
    )
    parser.add_argument("--input", required=True, help="Input image or PDF path")
    parser.add_argument("--output", required=True, help="Output PDF path")
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Render DPI for PDF inputs (higher == better OCR, larger output)",
    )
    parser.add_argument(
        "--predict-arg",
        action="append",
        default=[],
        help=(
            "Extra argument passed through to tools/infer/predict_system.py. "
            "Repeatable, e.g. --predict-arg --use_angle_cls=true"
        ),
    )
    parser.add_argument("--det-model-dir", default=os.environ.get("PADDLEOCR_DET_MODEL_DIR"))
    parser.add_argument("--rec-model-dir", default=os.environ.get("PADDLEOCR_REC_MODEL_DIR"))
    parser.add_argument(
        "--models-dir",
        default=os.environ.get("PADDLEOCR_MODELS_DIR", "/models"),
        help="Where to download models if det/rec dirs not provided",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="paddleocr_web_") as td:
        work_dir = Path(td)
        image_paths = _convert_input_to_images(input_path, work_dir=work_dir, dpi=args.dpi)

        det_dir = Path(args.det_model_dir) if args.det_model_dir else None
        rec_dir = Path(args.rec_model_dir) if args.rec_model_dir else None
        if not det_dir or not rec_dir:
            det_dir, rec_dir = _ensure_models(repo_root=repo_root, models_dir=Path(args.models_dir))

        pdf = fitz.open()
        try:
            for img_path in image_paths:
                w_px, h_px = _image_size_px(img_path)
                w_pt = w_px * 72.0 / args.dpi
                h_pt = h_px * 72.0 / args.dpi

                page = pdf.new_page(width=w_pt, height=h_pt)
                page.insert_image(page.rect, filename=str(img_path), keep_proportion=True)

                # OCR in pixel coordinates (top-left origin). Convert pixels -> points.
                lines = _run_predict_system(
                    repo_root=repo_root,
                    image_path=img_path,
                    work_dir=work_dir / img_path.stem,
                    extra_args=[
                        "--use_gpu=false",
                        "--det_model_dir",
                        str(det_dir),
                        "--rec_model_dir",
                        str(rec_dir),
                    ]
                    + args.predict_arg,
                )
                for line in lines:
                    x0, y0, x1, y1 = _bbox_from_points(line.points)
                    rect = fitz.Rect(
                        x0 * 72.0 / args.dpi,
                        y0 * 72.0 / args.dpi,
                        x1 * 72.0 / args.dpi,
                        y1 * 72.0 / args.dpi,
                    )
                    _insert_invisible_text(page, rect, line.text)

            pdf.save(str(output_path))
        finally:
            pdf.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

