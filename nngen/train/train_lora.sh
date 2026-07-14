#!/usr/bin/env bash
# Обучение hqiso SDXL LoRA на RTX 3080 Ti (12 GB). Запускать из корня репо
# при активированном venv с kohya sd-scripts (см. RUNBOOK.md).
# Ожидает переменную SD_SCRIPTS=путь к клону https://github.com/kohya-ss/sd-scripts
set -euo pipefail

SD_SCRIPTS="${SD_SCRIPTS:-$HOME/sd-scripts}"
MODEL="${MODEL:-stabilityai/stable-diffusion-xl-base-1.0}"
OUT_DIR="nngen/models"
mkdir -p "$OUT_DIR"

accelerate launch --num_cpu_threads_per_process 4 \
  "$SD_SCRIPTS/sdxl_train_network.py" \
  --pretrained_model_name_or_path "$MODEL" \
  --dataset_config nngen/train/dataset.toml \
  --output_dir "$OUT_DIR" \
  --output_name hqiso_lora \
  --network_module networks.lora \
  --network_dim 32 --network_alpha 16 \
  --learning_rate 1e-4 \
  --network_train_unet_only \
  --optimizer_type AdamW8bit \
  --lr_scheduler cosine --lr_warmup_steps 100 \
  --max_train_steps 2000 \
  --save_every_n_steps 500 \
  --mixed_precision bf16 --save_precision fp16 \
  --gradient_checkpointing \
  --cache_latents --cache_latents_to_disk \
  --cache_text_encoder_outputs --cache_text_encoder_outputs_to_disk \
  --sdpa \
  --max_data_loader_n_workers 2 \
  --seed 42 \
  --logging_dir nngen/train/logs

echo "Готово: $OUT_DIR/hqiso_lora.safetensors"
