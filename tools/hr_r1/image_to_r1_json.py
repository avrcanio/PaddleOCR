#!/usr/bin/env python3
"""
Slika -> PP-OCR (TextSystem) -> parse_receipt_text -> JSON na stdout.

Modeli: okolina PADDLEOCR_DET_MODEL_DIR, PADDLEOCR_REC_MODEL_DIR;
opcionalno PADDLEOCR_USE_ANGLE_CLS=true i PADDLEOCR_CLS_MODEL_DIR.
Zadano (Docker): /workspace/models/ch_PP-OCRv4_{det,rec}_infer ako env nije postavljen.

Opcionalno: generira searchable PDF iz ulazne slike putem `ocrmypdf` (slika + text layer).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
import shutil

__dir__ = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(__dir__, "..", ".."))
sys.path.insert(0, _REPO)
os.chdir(_REPO)
os.environ.setdefault("FLAGS_allocator_strategy", "auto_growth")


def _default_models() -> tuple[str, str]:
    det = os.environ.get("PADDLEOCR_DET_MODEL_DIR")
    rec = os.environ.get("PADDLEOCR_REC_MODEL_DIR")
    if not det:
        det = "/workspace/models/ch_PP-OCRv4_det_infer"
    if not rec:
        rec = "/workspace/models/ch_PP-OCRv4_rec_infer"
    return det, rec


def _build_infer_args():
    import tools.infer.utility as utility

    det, rec = _default_models()
    cls_dir = os.environ.get("PADDLEOCR_CLS_MODEL_DIR") or ""
    use_cls = os.environ.get("PADDLEOCR_USE_ANGLE_CLS", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if use_cls and not cls_dir:
        print(
            "PADDLEOCR_USE_ANGLE_CLS set but PADDLEOCR_CLS_MODEL_DIR is empty",
            file=sys.stderr,
        )
        sys.exit(2)

    rec_dict = os.path.join(_REPO, "ppocr", "utils", "ppocr_keys_v1.txt")
    font = os.path.join(_REPO, "doc", "fonts", "simfang.ttf")
    if not os.path.isfile(rec_dict):
        print(f"Missing dict: {rec_dict}", file=sys.stderr)
        sys.exit(2)

    argv_bak = sys.argv[:]
    infer_argv = [
        "image_to_r1_json.py",
        "--use_gpu",
        "false",
        "--use_angle_cls",
        "true" if use_cls else "false",
        "--det_model_dir",
        det,
        "--rec_model_dir",
        rec,
        "--rec_char_dict_path",
        rec_dict,
        "--vis_font_path",
        font if os.path.isfile(font) else "./doc/fonts/simfang.ttf",
        "--show_log",
        "false",
        "--benchmark",
        "false",
    ]
    if use_cls and cls_dir:
        infer_argv.extend(["--cls_model_dir", cls_dir])
    sys.argv = infer_argv
    try:
        return utility.parse_args()
    finally:
        sys.argv = argv_bak


def _ocr_lines(text_sys, img) -> list[str]:
    dt_boxes, rec_res, _ = text_sys(img)
    if dt_boxes is None or rec_res is None:
        return []
    return [rec_res[i][0] for i in range(len(rec_res))]


def _make_searchable_pdf(image_path: str, pdf_out: str, lang: str, image_dpi: int) -> None:
    cmd = [
        "ocrmypdf",
        "--skip-text",
        "--rotate-pages",
        "--deskew",
        "--image-dpi",
        str(image_dpi),
        "--output-type",
        "pdf",
    ]
    if lang:
        cmd.extend(["-l", lang])
    cmd.extend([image_path, pdf_out])
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        print(
            "ocrmypdf not found in PATH. Install ocrmypdf in the container/image.",
            file=sys.stderr,
        )
        sys.exit(2)
    except subprocess.CalledProcessError as e:
        print(f"ocrmypdf failed (exit {e.returncode})", file=sys.stderr)
        sys.exit(e.returncode or 1)


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _make_case_dir(root: Path) -> Path:
    case = root / f"case_{uuid.uuid4().hex[:12]}"
    case.mkdir(parents=True, exist_ok=False)
    return case


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Slika -> OCR -> hrvatski R-1 JSON (INA / Adria / Petrol)"
    )
    ap.add_argument("image", help="Putanja do slike (OpenCV imread)")
    ap.add_argument(
        "-o",
        "--output",
        help="Zapis JSON u datoteku (inače stdout)",
    )
    ap.add_argument(
        "--dump-ocr",
        action="store_true",
        help="Ispiše sirovi OCR tekst (linije) na stderr prije JSON-a",
    )
    ap.add_argument(
        "--dump-ocr-file",
        metavar="PATH",
        help="Zapis sirovog OCR teksta u datoteku",
    )
    ap.add_argument(
        "--pdf-out",
        metavar="PATH",
        help="Generira searchable PDF iz ulazne slike (ocrmypdf)",
    )
    ap.add_argument(
        "--pdf-lang",
        default=os.environ.get("OCRMY_PDF_LANG", "hrv+eng"),
        help="Tesseract jezici za ocrmypdf (zadano: OCRMY_PDF_LANG ili 'hrv+eng')",
    )
    ap.add_argument(
        "--pdf-image-dpi",
        type=int,
        default=int(os.environ.get("OCRMY_PDF_IMAGE_DPI", "300")),
        help="DPI za ulaznu sliku kad nema DPI metapodatke (zadano: 300; env OCRMY_PDF_IMAGE_DPI)",
    )
    ap.add_argument(
        "--artifact-dir",
        metavar="PATH",
        help="Spremi artefakte u postojeći folder (input.*, ocr.txt, parsed.json, out.pdf)",
    )
    ap.add_argument(
        "--artifact-root",
        metavar="PATH",
        help="Kreira novi case_<id> folder pod ovim rootom i spremi artefakte unutra",
    )
    args = ap.parse_args()

    import cv2

    from tools.hr_r1.r1_from_ocr import parse_receipt_text
    from tools.infer.predict_system import TextSystem

    infer_args = _build_infer_args()
    for name, path in (
        ("det", infer_args.det_model_dir),
        ("rec", infer_args.rec_model_dir),
    ):
        if not path or not os.path.isdir(path):
            print(f"Model dir ({name}) missing or not a directory: {path}", file=sys.stderr)
            sys.exit(2)
    if infer_args.use_angle_cls and (
        not infer_args.cls_model_dir or not os.path.isdir(infer_args.cls_model_dir)
    ):
        print(
            f"cls_model_dir missing or not a directory: {infer_args.cls_model_dir}",
            file=sys.stderr,
        )
        sys.exit(2)

    img = cv2.imread(args.image)
    if img is None:
        print(f"Cannot read image: {args.image}", file=sys.stderr)
        sys.exit(1)

    case_dir: Path | None = None
    if args.artifact_dir and args.artifact_root:
        print("Use only one of --artifact-dir or --artifact-root", file=sys.stderr)
        sys.exit(2)
    if args.artifact_root:
        case_dir = _make_case_dir(Path(args.artifact_root))
    elif args.artifact_dir:
        case_dir = Path(args.artifact_dir)
        _ensure_dir(case_dir)

    text_sys = TextSystem(infer_args)
    lines = _ocr_lines(text_sys, img)
    raw = "\n".join(lines)

    if case_dir:
        src = Path(args.image)
        ext = src.suffix if src.suffix else ".img"
        dst = case_dir / f"input{ext}"
        try:
            shutil.copy2(src, dst)
        except Exception as e:
            print(f"Failed to copy input image to artifacts dir: {e}", file=sys.stderr)
            sys.exit(2)

    if args.dump_ocr:
        print(raw, file=sys.stderr)
    ocr_out = args.dump_ocr_file
    if not ocr_out and case_dir:
        ocr_out = str(case_dir / "ocr.txt")
    if ocr_out:
        with open(ocr_out, "w", encoding="utf-8") as f:
            f.write(raw + ("\n" if raw and not raw.endswith("\n") else ""))

    pdf_out = args.pdf_out
    if not pdf_out and case_dir:
        pdf_out = str(case_dir / "out.pdf")
    if pdf_out:
        _make_searchable_pdf(args.image, pdf_out, args.pdf_lang, args.pdf_image_dpi)

    data = parse_receipt_text(raw)
    out = json.dumps(data, ensure_ascii=False, indent=2) + "\n"

    json_out = args.output
    if not json_out and case_dir:
        json_out = str(case_dir / "parsed.json")
    if json_out:
        with open(json_out, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        sys.stdout.write(out)

    if case_dir:
        # Print path so the caller can store it in logs/DB.
        print(f"artifacts_dir={case_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
