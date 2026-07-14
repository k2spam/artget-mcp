# Recraft — промпты для тайлсетов Heroquarium (стиль !image copy 10)

Цель: получить связный **top-down** пиксель-арт набор в тёплом уютном стиле референса
`references/world/!image copy 10.png` (Stardew/roguelike-town: слоёная трава, землистые
тропы, каменно-деревянные дома с черепицей, мягкое затенение, тёплая насыщенная палитра).

## Как гонять в Recraft
- Стиль: **Digital illustration → Pixel Art** (или Raster → Pixel art).
- Сначала сгенерируй **Промпт 0** (палитра-эталон). Понравившийся результат добавь как
  **свой стиль** (Recraft → Styles → создать из изображения) ИЛИ грузи `!image copy 10.png`
  как style-reference — тогда остальные листы выйдут в одной палитре.
- Размер холста 1024×1024. Фон — **прозрачный** (или ровный однотонный, потом вырежу).
- Каждый лист — **сетка одинаковых клеток**, объекты по центру клеток, БЕЗ текста и подписей.
- Целевой тайл — **32×32 px** (детальнее, чем наши текущие 16; при интеграции подгоню масштаб).
- Генерируй по 3–4 варианта на промпт, выбирай самый «сеточный» и чистый.

Общий хвост, добавляй в КАЖДЫЙ промпт:
> top-down orthographic view, cohesive warm palette, soft shading, subtle dark outlines,
> cozy fantasy village RPG, crisp pixel art, neat aligned grid of separate tiles,
> transparent background, no text, no labels, no watermark, consistent lighting from top-left.

---

## Промпт 0 — эталон палитры/стиля (для style-reference)
> A cozy top-down 2D fantasy RPG scene, hand-crafted pixel art: lush layered grass with
> darker mottled patches, worn dirt paths with pebble edges, a stone-and-timber cottage with
> a slate shingle roof, wooden fences, leafy round trees with soft shadows, flowers and bushes,
> warm saturated palette, gentle shading. Reference vibe: Stardew Valley meets classic roguelike.

## Промпт 1 — Террейн (земля и переходы)
> Seamless top-down terrain tileset, 32x32 tiles arranged in a neat grid: lush green grass
> (3–4 shade variants), autotile edges between grass and dirt, brown dirt path, grey cobblestone
> road, warm desert sand, dark forest floor, murky swamp mud, pale snow, rocky mountain floor,
> shallow-to-deep water with foamy shoreline transition tiles. Tileable edges, seamless.
> [+ общий хвост]

## Промпт 2 — Природа и мелкие детали
> Top-down nature props sprite sheet on transparent background, neat grid: several round leafy
> deciduous trees (light and dark green variants), pine/spruce trees, a palm tree, bushes and
> shrubs, tree stumps, mossy boulders and small rocks, tall grass tufts, reeds, colorful flower
> clusters, mushrooms, a bleached animal skull and scattered bones, a fallen log, a small pond
> plant. Each object centered in its own cell with a soft drop shadow. [+ общий хвост]

## Промпт 3 — Деревня: строения и утварь
> Top-down village building kit sprite sheet, transparent background, neat grid: small cottages
> with stone bases, timber-frame walls and slate shingle roofs (2–3 sizes and roof colors:
> slate-blue, red-tile, thatch), a market stall with striped awning, wooden fences and a gate,
> a stone well, wooden barrels and crates, a signpost, a hanging lantern on a post, a cozy
> tavern, a blacksmith forge, stacked firewood, hay bales, flower planters. Cohesive, cozy.
> [+ общий хвост]

## Промпт 4 — Вода, лодки, причалы
> Top-down water and harbor sprite sheet, transparent background, neat grid: wooden dock/pier
> plank tiles, dock posts, a small rowboat, a fishing boat with a mast and sail, water ripple
> and foam tiles, lily pads, a wooden bridge over a river, fishing nets, crab pots. Warm cozy
> pixel art matching a fantasy village. [+ общий хвост]

## Промпт 5 (опц.) — лагеря и подземелья за городом
> Top-down wilderness and camp props sprite sheet, transparent background, neat grid: canvas
> tents, a campfire with logs, a wooden palisade fence, a cave entrance in a rock face, ancient
> ruined stone arch, a treasure chest, a shrine, cracked bones and skulls, cacti, dead twisted
> trees. Cohesive cozy-but-slightly-ominous palette. [+ общий хвост]

---

## После генерации
Пришли листы сюда (в `references/` или прямо в чат). Я нарежу их на именованные тайлы,
заменю процедурную отрисовку в `renderer.ts` на спрайты (землю — на автотайлы, деревья/дома/
лодки — на спрайты), сохранив всю текущую логику (чанки, прозрачность деревьев, покачивание
лодок, y-сортировку). Если тайлы будут 32×32 — либо подниму размер тайла рендера, либо буду
рисовать пропсы крупнее клетки (как деревья сейчас), это несложно.
