## WSL2 (Docker) GPU fine-tune for PaddleOCR recognition (rec)

This folder contains a minimal Docker setup for running **PaddleOCR rec** training inside a GPU-enabled container (e.g. RTX 3090 via WSL2).

### Quick start

From the PaddleOCR repo root:

```bash
cd docker/wsl2-rec-train
mkdir -p data output
docker compose build
docker compose run --rm paddleocr python3 -c "import paddle; print(paddle.is_compiled_with_cuda()); print(paddle.device.get_device())"
```

### Training example (config + overrides)

```bash
cd docker/wsl2-rec-train
docker compose run --rm paddleocr python3 tools/train.py \
  -c configs/rec/PP-OCRv4/en_PP-OCRv4_mobile_rec.yml \
  -o Global.use_gpu=true Global.distributed=false \
     Global.save_model_dir=/workspace/output/rec_en_ppocrv4_finetune
```

Notes:
- `train_data/` is already ignored by repo `.gitignore`, so you can put your dataset under `train_data/` safely.
- `output/` here is a local folder (inside this `docker/wsl2-rec-train/`) mapped to `/workspace/output` in the container.
