# RUNBOOK — GPU-машина (RTX 3080 Ti)

Workflow: на слабой машине пишем код/датасет → commit/push → здесь pull →
обучение/генерация → commit результатов → pull обратно.

## 1. Окружение (один раз)

Рекомендую WSL2 (Ubuntu) — надёжнее для bitsandbytes; нативный Windows тоже
работает (тогда train_lora.sh запускать через Git Bash или переписать в .ps1).

```bash
# драйвер NVIDIA свежий; в WSL2 CUDA придёт из Windows-драйвера
git clone <репо> ~/ArtGen-MCP && cd ~/ArtGen-MCP

python3.11 -m venv ~/venv-nngen && source ~/venv-nngen/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r nngen/requirements-gpu.txt

# kohya sd-scripts (тренер)
git clone https://github.com/kohya-ss/sd-scripts ~/sd-scripts
cd ~/sd-scripts && pip install -r requirements.txt && cd -

accelerate config default   # или интерактивно: 1 GPU, bf16, no distributed

# проверка
python -c "import torch; print(torch.cuda.get_device_name(0), torch.cuda.is_available())"
```

## 2. Датасет

Датасет готовится на любой машине и коммитится:

```bash
python nngen/dataset/prepare.py     # → nngen/dataset/train/hqiso/*.png + *.txt
```

Если после pull папка `nngen/dataset/train/hqiso/` уже в репо — этот шаг здесь не нужен.

## 3. Обучение (~1.5–3 ч)

```bash
source ~/venv-nngen/bin/activate && cd ~/ArtGen-MCP
export SD_SCRIPTS=~/sd-scripts
bash nngen/train/train_lora.sh
```

- SDXL base (~7 GB) скачается с HuggingFace при первом запуске.
- OOM? — уменьшить в `train_lora.sh`: `--network_dim 16`, или resolution в
  `dataset.toml` до 896. Ошибка bitsandbytes на Windows → `--optimizer_type Lion`
  или поставить `bitsandbytes-windows`.
- Чекпойнты каждые 500 шагов: `nngen/models/hqiso_lora-000500.safetensors` и т.д.

## 4. Тест-генерация и выбор чекпойнта

```bash
python nngen/generate.py --prompt village --n 4
python nngen/generate.py --prompt house --n 4
# сравнить чекпойнты: временно переименовать hqiso_lora-001000 → hqiso_lora
```

Смотри `out/nngen/`. Критерии: палитра как в референсе, читаемая изометрия,
плотность деталей, нет «мыла» и фотореализма.

## 5. img2img по блокауту (главный режим)

```bash
python nngen/blockout.py out/iso_world_1_5x.png --out out/blockout.png
python nngen/generate.py --mode img2img --input out/blockout.png \
    --prompt village --strength 0.6 --n 4
```

`--strength`: 0.4–0.5 строго держит procgen-структуру, 0.6–0.7 добавляет
больше деталей ценой отклонений.

## 6. Коммит результатов

```bash
# один раз: git lfs install && git lfs track "*.safetensors"
git add nngen/models/hqiso_lora.safetensors out/nngen/ && \
git commit -m "nngen: trained hqiso lora vN + samples" && git push
```

В `out/` коммить только отобранные сэмплы (папка в .gitignore — добавлять через `git add -f`).

## 7. HTTP-воркер — генерация из Claude-сессии (MCP tool nn_generate)

Поднимает SDXL+LoRA как сервис в локальной сети; MCP-сервер на Mac ходит к нему.

На GPU-машине:
```bash
source ~/venv-nngen/bin/activate && cd ~/ArtGen-MCP
pip install fastapi uvicorn        # если ещё нет
python nngen/worker.py             # слушает 0.0.0.0:8188
```
- Windows спросит про firewall — разрешить для частной сети. (WSL2: ещё нужен
  проброс порта: `netsh interface portproxy add v4tov4 listenport=8188 connectaddress=<wsl-ip> connectport=8188` в админ-PowerShell.)
- Узнать IP машины: `ipconfig` → IPv4-адрес (вида 192.168.x.x).
- Проверка с Mac: открыть в браузере `http://<gpu-ip>:8188/health` — должно
  ответить `{"ok":true,"cuda":true,...}`.

На Mac (один раз):
```bash
echo "http://<gpu-ip>:8188" > nngen/endpoint.txt   # файл в .gitignore
```
Дальше в Claude-сессии доступен тул `nn_generate(prompt, mode, input_path,
strength, n)` — картинки сохраняются в `out/nngen_remote/`.

## Типовой цикл итерации

pull → (шаг 3 если менялся датасет/конфиг) → шаги 4–5 → push сэмплов →
обсуждаем в сессии → я правлю конфиг/датасет/промпты → снова pull.
