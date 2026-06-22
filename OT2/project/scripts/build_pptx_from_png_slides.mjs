import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));

async function pathExists(candidate) {
  try {
    await fs.access(candidate);
    return true;
  } catch {
    return false;
  }
}

async function findProjectRoot(start) {
  let current = start;
  while (true) {
    if (await pathExists(path.join(current, "final"))) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) {
      return start;
    }
    current = parent;
  }
}

async function findArtifactToolUtils() {
  const home = process.env.USERPROFILE || process.env.HOME || "C:/Users/liuwe";
  const base = path.join(home, ".codex", "plugins", "cache", "openai-primary-runtime", "presentations");
  const entries = await fs.readdir(base, { withFileTypes: true });
  const candidates = entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(base, entry.name, "skills", "presentations", "scripts", "artifact_tool_utils.mjs"))
    .sort()
    .reverse();
  for (const candidate of candidates) {
    if (await pathExists(candidate)) {
      return candidate;
    }
  }
  throw new Error(`Cannot find artifact_tool_utils.mjs under ${base}`);
}

const root = await findProjectRoot(scriptDir);
const pngDir = process.env.PNG_DIR
  ? path.resolve(root, process.env.PNG_DIR)
  : path.join(root, "project", "build", "rendered_png_slides");
const workspace = path.join(root, "project", "build", "coroutine-final-png-pptx-workspace");
const outDir = path.join(root, "final", "pptx");
const out = process.env.OUT_PPTX
  ? path.resolve(root, process.env.OUT_PPTX)
  : path.join(outDir, "协程技术调研-原版风格-修订版.pptx");
const slideSize = { width: 1280, height: 720 };
process.env.HOME = process.env.HOME || "C:/Users/liuwe";

const {
  createSlideContext,
  ensureArtifactToolWorkspace,
  importArtifactTool,
} = await import(pathToFileURL(await findArtifactToolUtils()).href);

await ensureArtifactToolWorkspace(workspace);
await fs.mkdir(outDir, { recursive: true });
const artifact = await importArtifactTool(workspace);
const { Presentation, PresentationFile } = artifact;
const presentation = Presentation.create({ slideSize });

const slideFiles = (await fs.readdir(pngDir))
  .filter((name) => /^slide_\d+\.png$/i.test(name))
  .sort();
const expectedSlides = process.env.EXPECTED_SLIDES ? Number(process.env.EXPECTED_SLIDES) : slideFiles.length;
if (slideFiles.length !== expectedSlides) {
  throw new Error(`Expected ${expectedSlides} PNG slides, found ${slideFiles.length}.`);
}

for (let index = 0; index < slideFiles.length; index += 1) {
  const slide = presentation.slides.add();
  const ctx = createSlideContext(artifact, {
    slideSize,
    slideNumber: index + 1,
    workspaceDir: workspace,
    outputDir: root,
    assetDir: path.join(root, "project", "assets"),
  });
  await ctx.addImage(slide, {
    path: path.join(pngDir, slideFiles[index]),
    x: 0,
    y: 0,
    width: 1280,
    height: 720,
    fit: "cover",
    alt: `Coroutine research slide ${index + 1}`,
  });
}

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(out);
const stat = await fs.stat(out);

await fs.writeFile(
  path.join(workspace, "manifest.json"),
  `${JSON.stringify({ out, bytes: stat.size, slideCount: presentation.slides.count, pngDir }, null, 2)}\n`,
  "utf8",
);

console.log(JSON.stringify({ out, bytes: stat.size, slideCount: presentation.slides.count, pngDir }, null, 2));
