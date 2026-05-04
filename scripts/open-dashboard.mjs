#!/usr/bin/env node
/**
 * scripts/open-dashboard.mjs
 * Run: npm run dashboard
 *
 * Opens the pipeline dashboard in your browser.
 * Reads data/pipeline.json and renders it as a visual HTML report.
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { execSync } from "child_process";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "..");

const PIPELINE_PATH   = path.join(ROOT, "data/pipeline.json");
const TEMPLATE_PATH   = path.join(ROOT, "templates/dashboard.html");
const OUTPUT_PATH     = path.join(ROOT, "data/dashboard_preview.html");

if (!fs.existsSync(PIPELINE_PATH)) {
  console.log("No pipeline.json found. Start tracking applications first.");
  process.exit(0);
}

const pipeline = JSON.parse(fs.readFileSync(PIPELINE_PATH, "utf8"));
const template = fs.readFileSync(TEMPLATE_PATH, "utf8");

const html = template.replace(
  "{{PIPELINE_DATA}}",
  JSON.stringify(pipeline)
);

fs.writeFileSync(OUTPUT_PATH, html);

// Open in default browser
const openCmd = process.platform === "darwin" ? "open" :
                process.platform === "win32"  ? "start" : "xdg-open";
try {
  execSync(`${openCmd} "${OUTPUT_PATH}"`, { stdio: "ignore" });
  console.log(`✅ Dashboard opened in browser.`);
  console.log(`   File: ${OUTPUT_PATH}`);
} catch {
  console.log(`Dashboard saved to: ${OUTPUT_PATH}`);
  console.log(`Open this file in your browser manually.`);
}
