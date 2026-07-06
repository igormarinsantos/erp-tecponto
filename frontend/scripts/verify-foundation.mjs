import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(fileURLToPath(new URL("..", import.meta.url)));
const appRoot = resolve(root, "..");
const publicDir = join(appRoot, "tecponto_app", "public", "frontend", "assets");
const requiredBuildFiles = ["app.js", "app.css"];
const requiredTokens = [
  "--tp-bg",
  "--tp-panel",
  "--tp-orange",
  "--tp-green",
  "--tp-blue",
  "--tp-purple",
  "--tp-amber",
  "--tp-red",
];
const forbiddenFrontendTerms = [
  "valuation_rate",
  "buying_rate",
  "purchase_rate",
  "gross_profit",
  "commission",
  "stock_value",
];

for (const file of requiredBuildFiles) {
  const target = join(publicDir, file);
  if (!existsSync(target)) {
    throw new Error(`Build ausente: ${target}`);
  }
}

const tokensPath = join(root, "src", "styles", "tokens.css");
const tokens = readFileSync(tokensPath, "utf8");
for (const token of requiredTokens) {
  if (!tokens.includes(token)) {
    throw new Error(`Token ausente: ${token}`);
  }
}

const sourceFiles = collectFiles(join(root, "src"));
for (const file of sourceFiles) {
  const body = readFileSync(file, "utf8");
  for (const term of forbiddenFrontendTerms) {
    if (body.includes(term)) {
      throw new Error(`Termo sensível no front (${term}): ${file}`);
    }
  }
}

console.log("Fundação frontend verificada: build, tokens e fonte sem termos sensíveis.");

function collectFiles(dir) {
  return readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      return collectFiles(path);
    }
    return path.endsWith(".ts") || path.endsWith(".tsx") || path.endsWith(".css") ? [path] : [];
  });
}
