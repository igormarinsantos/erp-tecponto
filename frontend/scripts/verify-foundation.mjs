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
const permittedOwnEarningsApi = join(root, "src", "api", "earnings.ts");
const permittedDirectorRegistryEditor = join(root, "src", "RegistryEditorModal.tsx");
const permittedDirectorRegistryTypes = join(root, "src", "api", "types.ts");
const permittedDirectorFinancialApi = join(root, "src", "api", "serviceOrders.ts");
const permittedDirectorFinancialView = join(root, "src", "App.tsx");

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
    // The technician may read only their already-generated earning entries.
    // Keep the backend method name isolated in this one typed API wrapper; all
    // other financial terms remain forbidden throughout the frontend source.
    if (term === "commission") {
      if (file === permittedOwnEarningsApi) {
        continue;
      }
      // This boolean is a feature switch, never an amount or payroll record.
      // Keep it available to hide commission-only UI when the operation opts out.
      if (!body.replaceAll("technician_commissions_enabled", "").replaceAll("commissionsEnabled", "").includes(term)) {
        continue;
      }
    }
    // The registry endpoint omits this key for every role except Diretor. The
    // modal may render that server-authorized, read-only value, while backend
    // tests prove the key never reaches Attendente or Técnico payloads.
    if (term === "valuation_rate" && (file === permittedDirectorRegistryEditor || file === permittedDirectorRegistryTypes)) {
      continue;
    }
    // Per-OS cost and result live behind the Director-only endpoint. Keep the
    // narrow exception restricted to its typed transport and this one view.
    if (["gross_profit", "cost"].includes(term) && (file === permittedDirectorFinancialApi || file === permittedDirectorFinancialView || file === permittedDirectorRegistryTypes)) {
      continue;
    }
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
