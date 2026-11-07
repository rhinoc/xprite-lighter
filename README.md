# @xprite/lighter

Generate normal maps, light masks, and relighted renders from pixel art.

Adapted from [Pixel Art Lighter v3.5.22](https://www.moonfell-rpg.com/Pixel-Art-Lighter-v3.5.22.html) by Red Hat Sprite (MIT, see `LICENSES/pixel-art-lighter-MIT.txt`).

## Usage

```ts
import {
  createNormalMapGenerator,
  generateNormalMap,
  defaultNormalMapOptions,
  createLightMaskGenerator,
  defaultLightMaskOptions,
  prepareNormalMapLighting,
  renderPreparedNormalMapLighting,
  renderNormalMapLighting,
  defaultNormalMapLightOptions,
} from "@xprite/lighter";
```

All functions take straight-alpha RGBA `PixelBuffer` inputs (`{ width, height, data: Uint8ClampedArray }`) and return new buffers.
