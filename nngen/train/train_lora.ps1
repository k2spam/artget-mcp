# Обучение hqiso SDXL LoRA — нативный Windows (RTX 3080 Ti, 12 GB).
# Запускать из корня репо при активированном venv (см. RUNBOOK.md).
# Требует: $env:SD_SCRIPTS = путь к клону kohya-ss/sd-scripts
$ErrorActionPreference = "Stop"

$SD_SCRIPTS = if ($env:SD_SCRIPTS) { $env:SD_SCRIPTS } else { "$HOME\sd-scripts" }
$MODEL      = if ($env:MODEL)      { $env:MODEL }      else { "stabilityai/stable-diffusion-xl-base-1.0" }
$OUT_DIR    = "nngen/models"
New-Item -ItemType Directory -Force -Path $OUT_DIR | Out-Null

accelerate launch --num_cpu_threads_per_process 4 `
  "$SD_SCRIPTS/sdxl_train_network.py" `
  --pretrained_model_name_or_path $MODEL `
  --dataset_config nngen/train/dataset.toml `
  --output_dir $OUT_DIR `
  --output_name hqiso_lora `
  --network_module networks.lora `
  --network_dim 32 --network_alpha 16 `
  --learning_rate 1e-4 `
  --network_train_unet_only `
  --optimizer_type AdamW8bit `
  --lr_scheduler cosine --lr_warmup_steps 100 `
  --max_train_steps 2000 `
  --save_every_n_steps 500 `
  --mixed_precision bf16 --save_precision fp16 `
  --gradient_checkpointing `
  --cache_latents --cache_latents_to_disk `
  --cache_text_encoder_outputs --cache_text_encoder_outputs_to_disk `
  --sdpa `
  --max_data_loader_n_workers 2 `
  --seed 42 `
  --logging_dir nngen/train/logs

# Ошибка bitsandbytes? Замените выше: --optimizer_type Lion (и уберите AdamW8bit)
Write-Host "Готово: $OUT_DIR/hqiso_lora.safetensors"
