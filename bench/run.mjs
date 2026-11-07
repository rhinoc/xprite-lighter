// Run @xprite/lighter plus competitor baselines against the bundled corpus.
// Usage: node bench/run.mjs [bench-dir] [out-dir] [method]
// method: object|character|terrain|architecture|spritelab|spritefusion|naive
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { PNG } from "pngjs";
import { generateNormalMap } from "../dist/index.js";
import { spriteLabNormalMap } from "./competitors/spritelab.mjs";
import { palNormalMap } from "./competitors/pal-upstream.mjs";
import { bumpItNormalMap } from "./competitors/bumpit.mjs";

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
  const png = new PNG({ width: buffer.width, height: buffer.height });
  png.data = Buffer.from(buffer.data.buffer, buffer.data.byteOffset, buffer.data.byteLength);
  writeFileSync(path, PNG.sync.write(png));
};

const methods = {
  object: (source) => generateNormalMap(source, { preset: "object" }),
  character: (source) => generateNormalMap(source, { preset: "character" }),
  terrain: (source) => generateNormalMap(source, { preset: "terrain" }),
  architecture: (source) => generateNormalMap(source, { preset: "architecture" }),
  spritelab: (source) => spriteLabNormalMap(source),
  "pal-upstream": (source) => palNormalMap(source, "object"),
  bumpit: (source) => bumpItNormalMap(source),
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

const generate = methods[method];
if (!generate) throw new Error(`unknown method "${method}"`);

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
