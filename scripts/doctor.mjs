#!/usr/bin/env node
/**
 * scripts/doctor.mjs
 * 
 * Checks everything is set up correctly before the user starts.
 * Run: npm run doctor
 * 
 * Checks: Node version, required files, AI CLI availability,
 * config completeness, data directory, Puppeteer install.
 */

import fs from "fs";
import path from "path";
import { execSync } from "child_process";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "..");

const GREEN  = "\x1b[32m";
const RED    = "\x1b[31m";
const YELLOW = "\x1b[33m";
const BLUE   = "\x1b[34m";
const BOLD   = "\x1b[1m";
const RESET  = "\x1b[0m";

let passed = 0, warned = 0, failed = 0;

function ok(label, detail = "")   { console.log(`  ${GREEN}✅${RESET} ${label}${detail ? `  ${YELLOW}→ ${detail}${RESET}` : ""}`); passed++; }
function warn(label, fix = "")    { console.log(`  ${YELLOW}⚠️  ${label}${RESET}${fix ? `\n     Fix: ${fix}` : ""}`); warned++; }
function fail(label, fix = "")    { console.log(`  ${RED}❌ ${label}${RESET}${fix ? `\n     Fix: ${fix}` : ""}`); failed++; }
function section(title)            { console.log(`\n${BOLD}${BLUE}── ${title}${RESET}`); }

console.log(`\n${BOLD}career-ops-india — Setup Doctor${RESET}`);
console.log(`Checking your environment...\n`);

// ── Node version ──────────────────────────────────────────────────────────────
section("Runtime");
const nodeVersion = process.versions.node.split(".").map(Number);
if (nodeVersion[0] >= 18) {
  ok(`Node.js ${process.versions.node}`, "v18+ required ✓");
} else {
  fail(`Node.js ${process.versions.node} is too old`, "Install Node 18+ from nodejs.org");
}

// ── Required files ────────────────────────────────────────────────────────────
section("Required files");

const requiredFiles = [
  ["cv.md",                    "Your CV — copy from templates/cv-template.md and fill in"],
  ["config/profile.yml",       "Your config — copy from config/profile.example.yml and fill in"],
  ["portals/india.yml",        "Company list — should exist in repo"],
  ["modes/evaluate.md",        "Evaluation mode — should exist in repo"],
  ["modes/_shared.md",         "Shared context — should exist in repo"],
  ["scripts/scan.mjs",         "Scanner script — should exist in repo"],
  ["scripts/generate-pdf.mjs", "PDF generator — should exist in repo"],
];

for (const [file, fix] of requiredFiles) {
  const fullPath = path.join(ROOT, file);
  if (fs.existsSync(fullPath)) {
    const size = fs.statSync(fullPath).size;
    if (size < 50) {
      warn(`${file} exists but looks empty (${size} bytes)`, `Fill in your details: ${file}`);
    } else {
      ok(file);
    }
  } else {
    fail(`${file} not found`, fix);
  }
}

// ── Config completeness ───────────────────────────────────────────────────────
section("Config validation");
const profilePath = path.join(ROOT, "config/profile.yml");
if (fs.existsSync(profilePath)) {
  const content = fs.readFileSync(profilePath, "utf8");
  const checks = [
    ["name:",          "Set your name in config/profile.yml"],
    ["target_roles:",  "Add target roles in config/profile.yml"],
    ["skills:",        "Add your skills in config/profile.yml"],
    ["min:",           "Set target salary range in config/profile.yml"],
  ];
  for (const [key, fix] of checks) {
    if (content.includes(key) && !content.includes(`${key} Your`) && !content.includes(`${key} []`)) {
      ok(`profile.yml → ${key.replace(":", "")} is set`);
    } else {
      warn(`profile.yml → ${key.replace(":", "")} may not be set`, fix);
    }
  }
} else {
  warn("Skipping config validation — profile.yml not found");
}

// ── CV content check ──────────────────────────────────────────────────────────
section("CV check");
const cvPath = path.join(ROOT, "cv.md");
if (fs.existsSync(cvPath)) {
  const cv = fs.readFileSync(cvPath, "utf8");
  if (cv.includes("Your Name") || cv.length < 300) {
    warn("cv.md looks like it hasn't been filled in yet", "Replace placeholder text with your real CV");
  } else {
    ok(`cv.md — ${cv.split("\n").length} lines`);
    if (!cv.match(/\d+%|\d+x|\d+\s*(hours|days|users|records|LPA|k\+)/i)) {
      warn("cv.md has no measurable results (numbers)", 'Add metrics: "reduced time by 40%", "processed 50K records", etc.');
    } else {
      ok("cv.md has quantified achievements ✓");
    }
  }
}

// ── AI CLI check ──────────────────────────────────────────────────────────────
section("AI CLI");
let claudeFound = false, geminiFound = false;

try {
  execSync("claude --version", { stdio: "pipe" });
  claudeFound = true;
  ok("Claude Code CLI is installed");
} catch {
  warn("Claude Code CLI not found", "Install from: https://claude.ai/code  (optional if using Gemini)");
}

try {
  execSync("gemini --version", { stdio: "pipe" });
  geminiFound = true;
  ok("Gemini CLI is installed");
} catch {
  warn("Gemini CLI not found", "Install from: https://github.com/google-gemini/gemini-cli  (optional if using Claude)");
}

if (!claudeFound && !geminiFound) {
  fail("No AI CLI found — you need at least one: Claude Code or Gemini CLI");
}

// ── Puppeteer (PDF generation) ────────────────────────────────────────────────
section("PDF generation (Puppeteer)");
try {
  const { execSync: es } = await import("child_process");
  execSync("node -e \"import('puppeteer').then(m => process.exit(0)).catch(() => process.exit(1))\"", 
    { stdio: "pipe", timeout: 5000 });
  ok("Puppeteer is installed");
} catch {
  warn(
    "Puppeteer not installed — PDF generation will not work",
    "Run: npm install  (then npm run pdf will work)"
  );
}

// ── Data directory ────────────────────────────────────────────────────────────
section("Data directory");
const dataDir = path.join(ROOT, "data");
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
  warn("data/ directory was missing — created it");
} else {
  ok("data/ directory exists");
}

const pipelinePath = path.join(ROOT, "data/pipeline.json");
if (!fs.existsSync(pipelinePath)) {
  fs.writeFileSync(pipelinePath, "[]");
  ok("data/pipeline.json created (empty)");
} else {
  try {
    const pipeline = JSON.parse(fs.readFileSync(pipelinePath, "utf8"));
    ok(`data/pipeline.json — ${pipeline.length} application(s) tracked`);
  } catch {
    fail("data/pipeline.json exists but is not valid JSON", "Run: npm run verify  to diagnose");
  }
}

// ── Output directories ────────────────────────────────────────────────────────
for (const dir of ["output", "reports"]) {
  const dirPath = path.join(ROOT, dir);
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
    ok(`${dir}/ created`);
  } else {
    ok(`${dir}/ exists`);
  }
}

// ── Final summary ─────────────────────────────────────────────────────────────
console.log(`\n${BOLD}── Summary${RESET}`);
console.log(`  ${GREEN}✅ Passed:   ${passed}${RESET}`);
if (warned) console.log(`  ${YELLOW}⚠️  Warnings: ${warned}${RESET}`);
if (failed) console.log(`  ${RED}❌ Failed:   ${failed}${RESET}`);

if (failed === 0 && warned <= 2) {
  console.log(`\n${GREEN}${BOLD}You're ready to go!${RESET}`);
  console.log(`Next steps:`);
  console.log(`  1. npm run scan          — find matching jobs at 60+ Indian companies`);
  console.log(`  2. Open Claude Code or Gemini CLI in this folder`);
  console.log(`  3. /evaluate [job URL]   — score any job against your profile\n`);
} else if (failed === 0) {
  console.log(`\n${YELLOW}${BOLD}Almost ready — fix the warnings above for best results.${RESET}`);
  console.log(`  Run: npm run scan  to get started anyway.\n`);
} else {
  console.log(`\n${RED}${BOLD}Fix the errors above before proceeding.${RESET}`);
  console.log(`  Re-run: npm run doctor  after fixing.\n`);
}
