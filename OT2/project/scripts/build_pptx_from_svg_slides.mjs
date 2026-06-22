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
const slidesDir = process.env.SLIDES_DIR
  ? path.resolve(root, process.env.SLIDES_DIR)
  : path.join(root, "final", "svg_slides");
const workspace = path.join(root, "project", "build", "coroutine-final-svg-pptx-workspace");
const previewDir = path.join(workspace, "preview");
const inlinedSlidesDir = path.join(workspace, "inlined_svg");
const outDir = path.join(root, "final", "pptx");
const out = process.env.OUT_PPTX
  ? path.resolve(root, process.env.OUT_PPTX)
  : path.join(outDir, "协程技术调研-原版风格.pptx");
const slideSize = { width: 1280, height: 720 };
process.env.HOME = process.env.HOME || "C:/Users/liuwe";

const {
  createSlideContext,
  ensureArtifactToolWorkspace,
  importArtifactTool,
  saveBlobToFile,
} = await import(pathToFileURL(await findArtifactToolUtils()).href);

await ensureArtifactToolWorkspace(workspace);
await fs.mkdir(outDir, { recursive: true });
const artifact = await importArtifactTool(workspace);
const { Presentation, PresentationFile } = artifact;
const presentation = Presentation.create({ slideSize });

const slideFiles = (await fs.readdir(slidesDir))
  .filter((name) => /^slide_\d+\.svg$/i.test(name))
  .sort();

const expectedSlides = process.env.EXPECTED_SLIDES ? Number(process.env.EXPECTED_SLIDES) : slideFiles.length;
if (slideFiles.length !== expectedSlides) {
  throw new Error(`Expected ${expectedSlides} SVG slides, found ${slideFiles.length}.`);
}

await fs.mkdir(previewDir, { recursive: true });
const previewPaths = [];

function inlineCssClasses(svgText) {
  const styleMatch = svgText.match(/<style>([\s\S]*?)<\/style>/);
  if (!styleMatch) {
    return svgText;
  }
  const classStyles = new Map();
  const classRulePattern = /\.([A-Za-z0-9_-]+)\s*\{([^}]*)\}/g;
  for (const match of styleMatch[1].matchAll(classRulePattern)) {
    const declarations = match[2].replace(/\s+/g, " ").trim();
    if (declarations) {
      classStyles.set(match[1], declarations);
    }
  }

  return svgText.replace(/<([A-Za-z][A-Za-z0-9:_-]*)([^>]*?)\sclass="([^"]+)"([^>]*)>/g, (full, tag, before, classes, after) => {
    const merged = classes
      .split(/\s+/)
      .map((name) => classStyles.get(name))
      .filter(Boolean)
      .join(" ");
    if (!merged) {
      return full;
    }
    const allAttrs = `${before} class="${classes}"${after}`;
    const styleMatch = allAttrs.match(/\sstyle="([^"]*)"/);
    if (styleMatch) {
      const nextAttrs = allAttrs.replace(/\sstyle="([^"]*)"/, ` style="${styleMatch[1].trim()} ${merged}"`);
      return `<${tag}${nextAttrs}>`;
    }
    return `<${tag}${allAttrs} style="${merged}">`;
  });
}

for (let index = 0; index < slideFiles.length; index += 1) {
  const svgPath = path.join(slidesDir, slideFiles[index]);
  const svgText = await fs.readFile(svgPath, "utf8");
  if (svgText.includes("<image") || svgText.includes("data:image") || svgText.includes("filter=")) {
    throw new Error(`SVG is not clean enough for direct PowerPoint insertion: ${svgPath}`);
  }
  await fs.mkdir(inlinedSlidesDir, { recursive: true });
  const inlinedSvgPath = path.join(inlinedSlidesDir, slideFiles[index]);
  await fs.writeFile(inlinedSvgPath, inlineCssClasses(svgText), "utf8");

  const slide = presentation.slides.add();
  const ctx = createSlideContext(artifact, {
    slideSize,
    slideNumber: index + 1,
    workspaceDir: workspace,
    outputDir: root,
    assetDir: path.join(root, "project", "assets"),
  });
  await ctx.addImage(slide, {
    path: inlinedSvgPath,
    x: 0,
    y: 0,
    width: 1280,
    height: 720,
    fit: "cover",
    alt: `Coroutine research slide ${index + 1}`,
  });
  const preview = await presentation.export({ slide, format: "png", scale: 1 });
  const previewPath = path.join(previewDir, `slide_${String(index + 1).padStart(2, "0")}.png`);
  await saveBlobToFile(preview, previewPath);
  previewPaths.push(previewPath);
}

const pptx = await PresentationFile.exportPptx(presentation);
const finalOut = out;
await pptx.save(finalOut);
const stat = await fs.stat(finalOut);

await fs.writeFile(
  path.join(workspace, "manifest.json"),
  `${JSON.stringify({ out: finalOut, bytes: stat.size, slideCount: presentation.slides.count, previewPaths, slidesDir }, null, 2)}\n`,
  "utf8",
);

console.log(JSON.stringify({ out: finalOut, bytes: stat.size, slideCount: presentation.slides.count, previewDir, slidesDir }, null, 2));
