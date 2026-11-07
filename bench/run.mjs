// Run @xprite/lighter against the bundled mesh-GT lighting corpus.
// Usage: node bench/run.mjs [bench-dir] [out-dir] [preset]
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { PNG } from "pngjs";
import { generateNormalMap } from "../dist/index.js";

const root = process.argv[2] ?? join(dirname(fileURLToPath(import.meta.url)));
const out = process.argv[3] ?? join(root, "run");
const preset = process.argv[4] ?? "object";

const manifest = JSON.parse(readFileSync(join(root, "manifest.json"), "utf8"));
mkdirSync(join(out, "normals"), { recursive: true });
const started = performance.now();
for (const c of manifest.cases) {
  const png = PNG.sync.read(readFileSync(join(root, "cases", c.id, "input.png")));
  const source = { width: png.width, height: png.height, data: new Uint8ClampedArray(png.data) };
  const normal = generateNormalMap(source, { preset });
  const encoded = new PNG({ width: normal.width, height: normal.height });
  encoded.data = Buffer.from(normal.data.buffer, normal.data.byteOffset, normal.data.byteLength);
  writeFileSync(join(out, "normals", `${c.id}.png`), PNG.sync.write(encoded));
}
const elapsed = (performance.now() - started) / 1000;
writeFileSync(
  join(out, "run.json"),
  JSON.stringify(
    { cases: manifest.cases.length, preset, seconds: Math.round(elapsed * 100) / 100 },
    null,
    2,
  ) + "\n",
);
console.log(`${manifest.cases.length} cases, preset=${preset}, ${elapsed.toFixed(2)}s`);
