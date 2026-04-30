## next-paddleocr-web

Simple Next.js UI that uploads a PDF/image, runs PaddleOCR on the server, and returns a **searchable PDF** for download.

### 1) Install Node deps

```bash
cd applications/next-paddleocr-web
npm install
```

### 2) Install Python deps

This app calls `tools/web/ocr_to_searchable_pdf.py`.

At minimum you need:

```bash
python3 -m pip install PyMuPDF Pillow
```

And you also need PaddleOCR runtime deps for `tools/infer/predict_system.py` (PaddlePaddle + model requirements). If you're setting up this repo for the first time, start from the repo's `requirements.txt` and/or official PaddleOCR install docs.

### 3) Run dev server

```bash
npm run dev
```

Open `http://localhost:3000`, upload a file, and your browser will download `*.ocr.pdf`.

### Notes

- Output PDF keeps the original page images, plus an **invisible text layer** (search/select).
- Large PDFs: processing time scales with page count and DPI (default 200).
- If OCR fails, the HTTP 500 body contains the Python stdout/stderr.

