// Run @xprite/lighter plus competitor baselines against the bundled corpus.
// Usage: node bench/run.mjs [bench-dir] [out-dir] [method]
// method: object|character|terrain|architecture|spritelab|spritefusion|naive
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { PNG } from "pngjs";
import {
  createLightMaskGenerator,
  estimatePaintedLight,
  estimatePaintedLightAngle,
  defaultNormalMapLightOptions,
  generateNormalMap,
  prepareNormalMapLighting,
  removePaintedLight,
  renderPreparedNormalMapLighting,
} from "../dist/index.js";
import { spriteLabNormalMap } from "./competitors/spritelab.mjs";
import { palNormalMap } from "./competitors/pal-upstream.mjs";
import { bumpItNormalMap } from "./competitors/bumpit.mjs";
import { laigterNormalMap } from "./competitors/laigter.mjs";

const root = process.argv[2] ?? join(dirname(fileURLToPath(import.meta.url)));
const out = process.argv[3] ?? join(root, "run");
const method = process.argv[4] ?? "object";

const SPRITEFUSION =
  process.env.SPRITEFUSION_BIN ??
  "/tmp/spritefusion-sprite-normals/target/release/spritefusion-sprite-normals";

const manifest = JSON.parse(readFileSync(join(root, "manifest.json"), "utf8"));
mkdirSync(join(out, "normals"), { recursive: true });

const readPng = (path) => {
  const png = PNG.sync.read(readFileSync(path));
  return { width: png.width, height: png.height, data: new Uint8ClampedArray(png.data) };
};
const writePng = (path, buffer) => {
  mkdirSync(dirname(path), { recursive: true });
  const png = new PNG({ width: buffer.width, height: buffer.height });
  png.data = Buffer.from(buffer.data.buffer, buffer.data.byteOffset, buffer.data.byteLength);
  writeFileSync(path, PNG.sync.write(png));
};

function renderMasked(source, id, { normals, mask }) {
  const prepared = prepareNormalMapLighting(source, normals, mask);
  const lights = {
    right: { x: source.width * 2, y: source.height * 0.3, height: 40 },
    top: { x: source.width / 2, y: -source.height * 0.8, height: 60 },
    bottom: { x: source.width * 0.4, y: source.height * 1.8, height: 40 },
    front: { x: source.width / 2, y: source.height / 2, height: 200 },
  };
  for (const [name, l] of Object.entries(lights)) {
    const frame = renderPreparedNormalMapLighting(prepared, {
      ...defaultNormalMapLightOptions(source.width, source.height),
      position: { x: l.x, y: l.y },
      height: l.height,
      brightness: 320,
      ambient: 22,
    });
    writePng(join(out, "relit", id, `${name}.png`), frame);
  }
  writePng(join(out, "masks", `${id}.png`), mask);
  return normals;
}

const methods = {
  object: (source) => generateNormalMap(source, { preset: "object" }),
  "object+hint": (source) => {
    const angle = estimatePaintedLightAngle(source);
    return generateNormalMap(source, {
      preset: "object",
      paintedLightAngle: angle ?? 135,
      paintedLightInfluence: angle === null ? 0 : (currentFlags.paintedLightInfluence ?? 60),
    });
  },
  "object+mask": (source, _inputPath, id) =>
    renderMasked(source, id, {
      normals: generateNormalMap(source, { preset: "object" }),
      mask: createLightMaskGenerator(source).generate(),
    }),
  // Divide the estimated painted light out of the input; run-relit.py then shades
  // out/albedo/<id>.png instead of the already-lit input.
  "object+delight": (source, _inputPath, id) => {
    const normals = generateNormalMap(source, { preset: "object" });
    const estimate = estimatePaintedLight(source);
    if (estimate)
      writePng(
        join(out, "albedo", `${id}.png`),
        removePaintedLight(prepareNormalMapLighting(source, normals), {
          angle: estimate.angle,
          influence: currentFlags.influence ?? 100,
        }),
      );
    return normals;
  },
  character: (source) => generateNormalMap(source, { preset: "character" }),
  terrain: (source) => generateNormalMap(source, { preset: "terrain" }),
  architecture: (source) => generateNormalMap(source, { preset: "architecture" }),
  spritelab: (source) => spriteLabNormalMap(source),
  "pal-upstream": (source) => palNormalMap(source, "object"),
  "pal-mask": (source, _inputPath, id) =>
    renderMasked(source, id, {
      normals: palNormalMap(source, "object"),
      mask: palNormalMap(source, "mask"),
    }),
  bumpit: (source) => bumpItNormalMap(source),
  laigter: (source) => laigterNormalMap(source),
  spritefusion: (_source, inputPath, id) => {
    const output = join(out, `${id}.spritefusion.png`);
    execFileSync(SPRITEFUSION, [inputPath, "-o", output, "--force"]);
    return readPng(output);
  },
  naive: (source) => {
    const data = new Uint8ClampedArray(source.data.length);
    for (let p = 0; p < source.width * source.height; p++) {
      const o = p * 4;
      data[o] = 128;
      data[o + 1] = 128;
      data[o + 2] = 255;
      data[o + 3] = source.data[o + 3];
    }
    return { width: source.width, height: source.height, data };
  },
};

const [base, flagstr] = method.split(":");
const [methodName, extraFlags] = base.split(",");
const flags = flagstr || extraFlags
  ? Object.fromEntries(
      (flagstr || extraFlags).split(",").map((kv) => {
        const [k, v] = kv.split("=");
        return [k, v === undefined || v === "" ? true : isNaN(+v) ? v : +v];
      }),
    )
  : {};
const methodImpl = methods[methodName] ?? methods[method];
// "+" methods manage their own options; "object:flag=..." goes through flag plumbing
const generate = methods[method]
  ? methodImpl
  : flagstr || extraFlags
    ? (source) =>
        generateNormalMap(source, {
          preset: base.split("+")[0],
          ...(flags.exp ? { experimental: flags.exp } : { experimental: flags }),
          ...flags,
        })
    : methodImpl;
if (!generate) throw new Error(`unknown method "${method}"`);

const currentFlags = flags;
const started = performance.now();
for (const c of manifest.cases) {
  const inputPath = join(root, "cases", c.id, "input.png");
  const normal = generate(readPng(inputPath), inputPath, c.id);
  writePng(join(out, "normals", `${c.id}.png`), normal);
}
const elapsed = (performance.now() - started) / 1000;
writeFileSync(
  join(out, "run.json"),
  JSON.stringify({ cases: manifest.cases.length, method, seconds: Math.round(elapsed * 100) / 100 }, null, 2) +
    "\n",
);
console.log(`${manifest.cases.length} cases, method=${method}, ${elapsed.toFixed(2)}s`);
