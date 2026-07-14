# Банк промптов hqiso (изометрия)

Все промпты начинаются с триггера: `hqiso, isometric pixel art, ` (generate.py
добавляет сам). Негатив общий: blurry, photo, 3d render, text, watermark, ui,
frame, deformed, oversaturated.

## Сцены
- **village** — cozy fantasy village, thatched and slate rooftops, stone-and-timber houses, winding dirt roads, river with wooden bridge, windmill, vegetable gardens, fences, lamp posts, lush trees, warm olive palette, dense charming details
- **farm** — farmstead, plowed vegetable beds in rows, barn, haystacks, scarecrow, chicken coop, wooden fences, dirt paths, warm olive palette
- **harbor** — riverside docks, wooden piers, moored rowboats, fishing nets, crates and barrels, stone embankment, warm olive palette
- **forest** — dense forest clearing, mixed oaks and pines, mossy boulders, mushrooms, fallen logs, winding trail, warm olive palette

## Объекты (на ровном травяном фоне — под вырезку)
- **house** — single cozy cottage, stone base, timber-frame walls, detailed thatched roof, chimney with smoke, flower beds, plain grass background
- **windmill** — tall stone windmill with wooden blades, plain grass background
- **nature** — набор: leafy trees, pines, bushes, boulders, flowers, stumps, plain grass background
- **villager** — single villager character, full body, front view, simple pose, plain background, game sprite

## Догенерация референсов для датасета (Recraft/Craiyon)
Пока LoRA не обучена, добираем датасет внешними сервисами. Промпт-каркас:

> isometric pixel art of a cozy medieval fantasy village, thatched cottages
> with detailed rooftops, dirt roads, river, windmill, gardens, fences,
> lamp posts, lush trees, warm olive-green palette, soft shading, dark
> outlines, dense charming details, high detail, no text, no watermark

Вариации: harbor district / farm fields / winter version / market square /
forest hamlet / stone castle courtyard. Класть в `references/iso/`,
дописывать строку в `dataset/sources.txt`, перегонять `prepare.py`.

## Заметки по параметрам
- txt2img: steps 30, cfg 6–7. Выше cfg → пересыщенные цвета.
- img2img: strength 0.55–0.65 — баланс структура/детали.
- LoRA weight по умолчанию 1.0; если стиль «съедает» структуру — 0.8.
