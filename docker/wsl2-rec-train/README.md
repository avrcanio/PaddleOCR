## Docker (CPU) — inference with trained models

NVIDIA/CUDA **nije** potreban. Kontejner služi za **pokretanje već istreniranih modela** (det/rec/…) na CPU-u.

### Priprema

```bash
cd docker/wsl2-rec-train
mkdir -p models data output
# kopiraj inference ili trenirane težine u ./models (ili koristi apsolutne putanje u CLI)
docker compose up -d --build
```

### Primjer: provjera Paddle-a

```bash
docker compose exec paddleocr python3 -c "import paddle; print(paddle.__version__, paddle.is_compiled_with_cuda())"
```

### Primjer: inference (prilagodi putanje modela)

```bash
docker compose exec paddleocr python3 tools/infer/predict_system.py \
  --image_dir=/workspace/data \
  --det_model_dir=/workspace/models/ch_PP-OCRv4_det_infer \
  --rec_model_dir=/workspace/models/ch_PP-OCRv4_rec_infer \
  --cls_model_dir=/workspace/models/ch_ppocr_mobile_v2.0_cls_infer
```

Volumei:

- `../../` → kod PaddleOCR-a
- `./models` → `/workspace/models` (težine)
- `./data` → ulazne slike/dokumenti
- `./output` → rezultati (po želji)
