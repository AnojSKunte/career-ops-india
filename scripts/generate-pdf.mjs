#!/usr/bin/env node
/**
 * scripts/generate-pdf.mjs
 * 
 * Generates an ATS-optimized PDF resume from cv.md + job context.
 * Uses Puppeteer to render the HTML template and export to PDF.
 * 
 * Run:  npm run pdf                          — interactive mode
 * Run:  npm run pdf -- --company razorpay    — direct mode
 * 
 * The AI (Claude/Gemini) calls this after tailoring the CV content.
 * You can also run it standalone with a pre-tailored cv.md.
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "..");

// ── Args ──────────────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const getArg = (flag) => {
  const i = args.indexOf(flag);
  return i !== -1 ? args[i + 1] : null;
};

const company   = getArg("--company")  || "general";
const role      = getArg("--role")     || "application";
const inputFile = getArg("--input")    || path.join(ROOT, "cv.md");
const outputDir = getArg("--output")   || path.join(ROOT, "output");

// ── Read CV ───────────────────────────────────────────────────────────────────
if (!fs.existsSync(inputFile)) {
  console.error(`❌ CV file not found: ${inputFile}`);
  console.error(`   Create cv.md in the project root first.`);
  process.exit(1);
}

const cvMarkdown = fs.readFileSync(inputFile, "utf8");

// ── Markdown → HTML (minimal parser for CV structure) ─────────────────────────
function mdToHtml(md) {
  return md
    .replace(/^# (.+)$/gm,       '<h1>$1</h1>')
    .replace(/^## (.+)$/gm,      '<h2>$1</h2>')
    .replace(/^### (.+)$/gm,     '<h3>$1</h3>')
    .replace(/\*\*(.+?)\*\*/g,   '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,       '<em>$1</em>')
    .replace(/^- (.+)$/gm,       '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, s => `<ul>${s}</ul>`)
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2">$1</a>')
    .replace(/`(.+?)`/g,         '<code>$1</code>')
    .replace(/^---$/gm,          '<hr>')
    .replace(/^\*(.+)\*$/gm,     '<p class="date">$1</p>')
    .replace(/\n\n/g,            '</p><p>')
    .replace(/^(?!<[hpulodc])/gm, '')
    .replace(/<\/p>\s*<p>(?=<[hul])/g, '')
    .replace(/^<\/p><p>$/gm,     '');
}

// ── Read HTML template ────────────────────────────────────────────────────────
const templatePath = path.join(ROOT, "templates/cv-template.html");
if (!fs.existsSync(templatePath)) {
  console.error(`❌ Template not found: ${templatePath}`);
  process.exit(1);
}
const template = fs.readFileSync(templatePath, "utf8");

// ── Inject CV content into template ──────────────────────────────────────────
const htmlContent = template.replace("{{CV_CONTENT}}", mdToHtml(cvMarkdown));

// ── Generate PDF with Puppeteer ───────────────────────────────────────────────
let puppeteer;
try {
  puppeteer = (await import("puppeteer")).default;
} catch {
  console.error("❌ Puppeteer not installed. Run: npm install");
  process.exit(1);
}

fs.mkdirSync(outputDir, { recursive: true });

const safeCompany = company.toLowerCase().replace(/[^a-z0-9]/g, "-");
const safeRole    = role.toLowerCase().replace(/[^a-z0-9]/g, "-");
const date        = new Date().toISOString().split("T")[0];
const filename    = `anoj-sk_${safeCompany}_${safeRole}_${date}.pdf`;
const outputPath  = path.join(outputDir, filename);

console.log(`\n📄 Generating PDF...`);
console.log(`   Company: ${company}`);
console.log(`   Role:    ${role}`);
console.log(`   Output:  ${outputPath}\n`);

const browser = await puppeteer.launch({ headless: true, args: ["--no-sandbox"] });
const page    = await browser.newPage();

await page.setContent(htmlContent, { waitUntil: "networkidle0" });

await page.pdf({
  path: outputPath,
  format: "A4",
  printBackground: true,
  margin: { top: "12mm", right: "14mm", bottom: "12mm", left: "14mm" },
  displayHeaderFooter: false,
});

await browser.close();

const sizeKb = Math.round(fs.statSync(outputPath).size / 1024);
console.log(`✅ PDF saved: ${filename}  (${sizeKb} KB)`);
console.log(`\nATS tip: File is under 1MB and text-only — safe for all Indian ATS systems.`);
console.log(`Upload path: ${outputPath}\n`);
