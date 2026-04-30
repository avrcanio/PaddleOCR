"use client";

import { useMemo, useState } from "react";

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>("");

  const accept = useMemo(() => ".pdf,.png,.jpg,.jpeg,.bmp,.tif,.tiff,.webp", []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!file) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.set("file", file);
      const res = await fetch("/api/ocr", { method: "POST", body: fd });
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(msg || `Request failed (${res.status})`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const base = (file.name || "output").replace(/\.[^/.]+$/, "");
      a.href = url;
      a.download = `${base}.ocr.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="container">
      <div className="header">
        <h1 className="title">PaddleOCR → Searchable PDF</h1>
        <p className="subtitle">
          Upload a PDF or image. The server runs PaddleOCR and returns a searchable PDF (original
          image(s) + invisible text layer).
        </p>
      </div>

      <section className="card">
        <form onSubmit={onSubmit}>
          <div className="row">
            <input
              className="input"
              type="file"
              accept={accept}
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              disabled={busy}
              required
            />
            <button className="button" type="submit" disabled={busy || !file}>
              {busy ? "Running OCR…" : "Upload & Download PDF"}
            </button>
          </div>
          <div className="hint">
            Supported: PDF, PNG, JPG/JPEG, BMP, TIF/TIFF, WebP. Large PDFs can take a while because
            OCR runs per page.
          </div>
          {error ? <div className="error">{error}</div> : null}
          <div className="footer">
            Tip: if OCR fails, open server logs — most commonly Python deps or model downloads.
          </div>
        </form>
      </section>
    </main>
  );
}

