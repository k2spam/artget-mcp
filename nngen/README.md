# nngen — нейросетевой пайплайн (M6)

Цель: генерация изометрического пиксель-арта уровня референса
(`references/iso/`) — тёплая оливковая палитра, высокая плотность деталей,
бесконечное разнообразие — при сохранении контроля структуры сцены со стороны procgen.

## Архитектура

```
референсы (iso)               procgen (artgen/iso.py)
      │                              │
      ▼                              ▼
dataset/prepare.py            blockout.py (семантический рендер сцены)
      │                              │
      ▼                              ▼
train/ (kohya, SDXL LoRA)  →  generate.py ──ControlNet/img2img──► детальный арт
   «hqiso» style                                                     │
                                                                     ▼
                                                  artgen/pixelize.py (квантизация в палитру)
                                                                     ▼
                                                  нарезка чанков/спрайтов → игра
```

Решения (2026-07-15):
- **Только изометрия.** Топ-даун ветка закрыта.
- **Не пишем сеть с нуля** — style-LoRA поверх SDXL. Позже, при нужде в скорости,
  дистилляция в маленький pix2pix (блокаут→арт) на парах, сгенерированных SDXL.
- **Обучение на GPU-машине (RTX 3080 Ti, 12 GB)** через git: здесь пишем код и
  конфиги, там `git pull` → тренируем/генерим по `RUNBOOK.md` → коммитим результаты.
- Trigger word стиля: **`hqiso`**.

## Состав

| Путь | Что делает |
|---|---|
| `dataset/sources.txt` | список iso-референсов (+ тэги) для датасета |
| `dataset/prepare.py` | кропы 1024² с фильтром пустых, caption-файлы |
| `train/dataset.toml` | kohya dataset config |
| `train/train_lora.sh` | запуск обучения SDXL LoRA (под 12 GB) |
| `generate.py` | txt2img / img2img(блокаут) с LoRA, diffusers |
| `blockout.py` | подготовка блокаута из procgen-рендера |
| `prompts.md` | банк промптов hqiso |
| `RUNBOOK.md` | инструкция для GPU-машины |
| `requirements-gpu.txt` | зависимости GPU-машины |

## Порядок работы

1. Пополнить `references/iso/` (см. `dataset/sources.txt`), запустить `dataset/prepare.py` — можно на любой машине.
2. Закоммитить датасет, на GPU-машине — `RUNBOOK.md` шаги 1–3 (окружение + обучение, ~1.5–3 ч).
3. Закоммитить `models/hqiso_lora.safetensors` (git lfs), генерить через `generate.py`.
4. Итерации качества: добор датасета → дообучение → сравнение сеток превью.
