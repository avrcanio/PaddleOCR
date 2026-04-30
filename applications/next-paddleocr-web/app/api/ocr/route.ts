import { spawn } from "node:child_process";
import { promises as fs } from "node:fs";
import { existsSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { randomUUID } from "node:crypto";

export const runtime = "nodejs";

const REPO_ROOT =
  process.env.PADDLEOCR_REPO_ROOT ?? path.resolve(process.cwd(), "..", ".."); // local dev fallback
const PY_SCRIPT = path.join(REPO_ROOT, "tools", "web", "ocr_to_searchable_pdf.py");
const PYTHON_CMD =
  process.env.PADDLEOCR_PYTHON_CMD ??
  (existsSync("/opt/venv/bin/python") ? "/opt/venv/bin/python" : "python3");

function run(
  cmd: string,
  args: string[],
  opts: { cwd?: string; timeoutMs?: number } = {}
) {
  return new Promise<{ code: number; output: string }>((resolve) => {
    const p = spawn(cmd, args, {
      cwd: opts.cwd,
      stdio: ["ignore", "pipe", "pipe"]
    });
    let out = "";
    p.stdout.on("data", (d) => (out += d.toString()));
    p.stderr.on("data", (d) => (out += d.toString()));
    p.on("error", (err) => {
      resolve({
        code: 1,
        output:
          `Failed to start process '${cmd}'. ` +
          `Is it installed in the container?\n\n${String(err)}`
      });
    });
    const timeout =
      opts.timeoutMs && opts.timeoutMs > 0
        ? setTimeout(() => {
            try {
              p.kill("SIGKILL");
            } catch {
              // ignore
            }
            resolve({
              code: 1,
              output: `OCR timed out after ${opts.timeoutMs}ms.`
            });
          }, opts.timeoutMs)
        : null;
    p.on("close", (code) => resolve({ code: code ?? 1, output: out }));
    p.on("close", () => {
      if (timeout) clearTimeout(timeout);
    });
  });
}

export async function POST(req: Request) {
  const fd = await req.formData();
  const f = fd.get("file");
  if (!(f instanceof File)) {
    return new Response("Missing form field 'file'.", { status: 400 });
  }

  const ext = path.extname(f.name || "").toLowerCase() || ".bin";
  const jobId = randomUUID();
  const tmpDir = path.join(os.tmpdir(), "next-paddleocr-web");
  await fs.mkdir(tmpDir, { recursive: true });

  const inputPath = path.join(tmpDir, `${jobId}${ext}`);
  const outputPath = path.join(tmpDir, `${jobId}.pdf`);

  try {
    const buf = Buffer.from(await f.arrayBuffer());
    await fs.writeFile(inputPath, buf);

    // NOTE: Uses python3 and expects PaddleOCR deps/models to be installed in the environment.
    const { code, output } = await run(
      PYTHON_CMD,
      [PY_SCRIPT, "--input", inputPath, "--output", outputPath],
      { cwd: REPO_ROOT, timeoutMs: 15 * 60 * 1000 }
    );

    if (code !== 0) {
      await fs.rm(outputPath, { force: true }).catch(() => undefined);
      return new Response(output || "OCR failed.", { status: 500 });
    }

    const hasOutput = await fs
      .stat(outputPath)
      .then(() => true)
      .catch(() => false);
    if (!hasOutput) {
      return new Response(
        [
          "OCR process finished but output PDF was not created.",
          `Expected: ${outputPath}`,
          "",
          "Process output:",
          output || "(no output)"
        ].join("\n"),
        { status: 500 }
      );
    }

    const pdf = await fs.readFile(outputPath);
    await fs.rm(outputPath, { force: true }).catch(() => undefined);

    return new Response(pdf, {
      status: 200,
      headers: {
        "content-type": "application/pdf",
        "content-disposition": `attachment; filename="output.ocr.pdf"`
      }
    });
  } catch (e) {
    const msg = e instanceof Error ? `${e.name}: ${e.message}` : String(e);
    return new Response(msg, { status: 500 });
  } finally {
    // Cleanup input regardless of success.
    await fs.rm(inputPath, { force: true }).catch(() => undefined);
    await fs.rm(outputPath, { force: true }).catch(() => undefined);
  }
}

