// Render the OGA monsters sheet with @xprite/lighter: generated normals vs the
// artist's authored normals, relit at several light angles. Writes demo/out/*.png.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { PNG } from "pngjs";
import {
  generateNormalMap,
  prepareNormalMapLighting,
  renderPreparedNormalMapLighting,
} from "../dist/index.js";

const here = dirname(fileURLToPath(import.meta.url));
const out = join(here, "out");
mkdirSync(out, { recursive: true });

const read = (name) => {
  const png = PNG.sync.read(readFileSync(join(here, "assets", name)));
  return { width: png.width, height: png.height, data: new Uint8ClampedArray(png.data) };
};
const write = (name, buffer) => {
  const png = new PNG({ width: buffer.width, height: buffer.height });
  png.data = Buffer.from(buffer.data.buffer, buffer.data.byteOffset, buffer.data.byteLength);
  writeFileSync(join(out, name), PNG.sync.write(png));
};

const albedo = read("oga-10-monsters-render-cutout.png");
const authored = read("oga-10-monsters-normals-cutout.png");
const generated = generateNormalMap(albedo, { preset: "object" });

// Crop to the Shadow Boss row so per-pixel lighting is visible at 100%.
const CROP = { x: 4, y: 1004, w: 336, h: 108 };
const crop = (buffer) => {
  const data = new Uint8ClampedArray(CROP.w * CROP.h * 4);
  for (let y = 0; y < CROP.h; y++) {
    const src = ((CROP.y + y) * buffer.width + CROP.x) * 4;
    data.set(buffer.data.subarray(src, src + CROP.w * 4), y * CROP.w * 4);
  }
  return { width: CROP.w, height: CROP.h, data };
};

write("normals-generated.png", generated);
write("normals-authored.png", authored);
write("albedo-boss.png", crop(albedo));
write("normals-generated-boss.png", crop(generated));
write("normals-authored-boss.png", crop(authored));

// Keep the light above the horizon and sweep azimuth for a lively loop.
const light = (azimuthDeg, elevationDeg = 55) => {
  const az = (azimuthDeg * Math.PI) / 180;
  const el = (elevationDeg * Math.PI) / 180;
  const radius = Math.cos(el);
  const z = Math.sin(el);
  // position in sprite plane; height is the light's z over the plane
  return { x: (Math.cos(az) * radius * albedo.width) / 2, y: (-Math.sin(az) * radius * albedo.height) / 2, z };
};

const FRAMES = 24;
for (const [name, normals] of [
  ["generated", generated],
  ["authored", authored],
]) {
  const sprite = crop(albedo);
  const prepared = prepareNormalMapLighting(sprite, crop(normals));
  for (let i = 0; i < FRAMES; i++) {
    const az = (i / FRAMES) * 360;
    const p = light(az);
    const frame = renderPreparedNormalMapLighting(prepared, {
      position: { x: sprite.width / 2 + (p.x * sprite.width) / albedo.width, y: sprite.height / 2 + (p.y * sprite.height) / albedo.height },
      height: 60 + 60 * p.z,
      brightness: 380,
      ambient: 10,
      maskStrength: 100,
      color: [255, 244, 224, 255],
      invertY: false,
    });
    write(`relit-${name}-${String(i).padStart(2, "0")}.png`, frame);
  }
}
console.log(`wrote ${2 + FRAMES * 2} images to ${out}`);
