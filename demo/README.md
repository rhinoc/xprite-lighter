# Demo

Relights a third-party sprite sheet whose pack already ships artist-authored
normal maps — handy for eyeballing what `generateNormalMap` recovers from the
flat render. The authored maps are procedurally generated upstream, so this is a
presentation demo, not a scored benchmark (see `bench/` for scored evaluation).

## Build

```sh
pnpm run build        # package first — the demo imports dist/
pnpm run demo         # writes demo/out/*.png
```

Open `demo/index.html` and drag the slider to orbit the light over
authored-vs-generated normals.

## Assets

`assets/oga-10-monsters-*` comes from
[10 More Fantasy RPG Enemies Plus a Boss — Normal Map](https://opengameart.org/content/10-more-fantasy-rpg-enemies-plus-a-boss-normal-map)
by **Antifarea**, licensed **CC-BY 3.0**. `*-cutout.png` files are derived copies
where the dark background was flood-filled to transparent and the header text was
cropped; sprite pixels are unmodified.
