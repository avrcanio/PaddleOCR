# Hrvatski R-1 / maloprodajni računi (INA, Adria Oil, Petrol)

Mapa `tools/hr_r1/` služi za **parsiranje već izvučenog OCR ili PDF teksta** u jedinstveni JSON oblik. Radi **odvojeno** od glavnog PaddleOCR pipelinea (najprije dobiješ `.txt` ili sličan tekst, zatim ovaj alat).

## Pokretanje

Iz ove mape:

```bash
cd /opt/stacks/PaddleOCR/tools/hr_r1
python3 r1_from_ocr.py /put/do/page-1.txt -o out.json
```

Ulaz može biti i PDF (ako je dostupan `pdftotext` u `PATH`):

```bash
python3 r1_from_ocr.py "racun.pdf" -o out.json
```

Ili stdin:

```bash
cat page-1.txt | python3 r1_from_ocr.py -
```

Detalji korištenja: docstring na vrhu `r1_from_ocr.py`.

## Slika → OCR → R-1 JSON (`image_to_r1_json.py`)

Jedan korak: **PP-OCR** na slici, zatim isti parser kao `r1_from_ocr.py`. JSON ide na **stdout** (ili `-o`).

```bash
cd /opt/stacks/PaddleOCR
export PADDLEOCR_DET_MODEL_DIR=/put/do/ch_PP-OCRv4_det_infer
export PADDLEOCR_REC_MODEL_DIR=/put/do/ch_PP-OCRv4_rec_infer
# opcionalno: kut teksta
# export PADDLEOCR_USE_ANGLE_CLS=true
# export PADDLEOCR_CLS_MODEL_DIR=/put/do/ch_ppocr_mobile_v2.0_cls_infer

python3 tools/hr_r1/image_to_r1_json.py /put/do/racun.png -o out.json
```

Debug OCR teksta (ne mijenja JSON na stdout):

```bash
python3 tools/hr_r1/image_to_r1_json.py racun.png --dump-ocr
python3 tools/hr_r1/image_to_r1_json.py racun.png --dump-ocr-file /tmp/ocr.txt -o out.json
```

Searchable PDF (slika + OCR text layer) preko `ocrmypdf`:

```bash
python3 tools/hr_r1/image_to_r1_json.py racun.png \
  --pdf-out out.pdf \
  --pdf-lang hrv+eng \
  -o out.json
```

Ako env varijable nisu postavljene, zadani putovi u kontejneru su  
`/workspace/models/ch_PP-OCRv4_det_infer` i  
`/workspace/models/ch_PP-OCRv4_rec_infer`.

### Docker (`paddleocr` kontejner)

Spremi sliku u mapu koju kontejner vidi (npr. volume `data` → `/workspace/data`):

```bash
docker compose -f docker/wsl2-rec-train/docker-compose.yml exec -T paddleocr \
  python3 /workspace/PaddleOCR/tools/hr_r1/image_to_r1_json.py \
  /workspace/data/racun.png
```

Jedna naredba za **JSON + PDF** (spremi u `/workspace/output`, koji je volume `output`):

```bash
docker compose -f docker/wsl2-rec-train/docker-compose.yml exec -T paddleocr \
  python3 /workspace/PaddleOCR/tools/hr_r1/image_to_r1_json.py \
  /workspace/data/racun.png \
  -o /workspace/output/out.json \
  --pdf-out /workspace/output/out.pdf
```

### Automatsko spremanje artefakata (za tuning)

Ako želiš da se za svaki poziv automatski spremi:
- ulazna slika (`input.*`)
- OCR tekst (`ocr.txt`)
- parsirani JSON (`parsed.json`)
- PDF (`out.pdf`)

koristi `--artifact-root` (kreira novi `case_<id>` folder):

```bash
docker compose -f docker/wsl2-rec-train/docker-compose.yml exec -T paddleocr \
  python3 /workspace/PaddleOCR/tools/hr_r1/image_to_r1_json.py \
  /workspace/data/racun.png \
  --artifact-root /workspace/PaddleOCR/train_data/hr_r1_tuning
```

Skripta će na `stderr` ispisati gdje je spremila artefakte, npr. `artifacts_dir=/workspace/PaddleOCR/train_data/hr_r1_tuning/case_...`.

Izlaz JSON uhvati na hostu (npr. preusmjeravanje stdout-a u skripti koja poziva `docker compose exec`).
