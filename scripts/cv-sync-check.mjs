#!/usr/bin/env node
/**
 * scripts/cv-sync-check.mjs
 * Run: npm run sync-check
 *
 * Checks that your cv.md and config/profile.yml are consistent.
 * Common issue: you update your skills list in profile.yml but forget
 * to add them to cv.md (or vice versa). The AI then evaluates you
 * on skills that don't appear in your actual resume.
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "..");

const cvPath      = path.join(ROOT, "cv.md");
const profilePath = path.join(ROOT, "config/profile.yml");

if (!fs.existsSync(cvPath) || !fs.existsSync(profilePath)) {
  console.log("❌ cv.md or config/profile.yml not found."); process.exit(1);
}

const cv      = fs.readFileSync(cvPath, "utf8").toLowerCase();
const profile = fs.readFileSync(profilePath, "utf8");

// Extract skills from profile.yml
const skillsMatch = profile.match(/skills:\s*\n((?:\s*-\s*.+\n?)+)/);
if (!skillsMatch) { console.log("⚠️  Could not find skills list in profile.yml"); process.exit(0); }

const skills = skillsMatch[1]
  .split("\n")
  .map(l => l.replace(/^\s*-\s*/, "").trim().toLowerCase())
  .filter(Boolean);

console.log(`\n\x1b[1mCV ↔ Profile Sync Check\x1b[0m`);
console.log(`Checking ${skills.length} skills from profile.yml against cv.md...\n`);

const inCV     = [];
const notInCV  = [];

for (const skill of skills) {
  if (cv.includes(skill)) {
    inCV.push(skill);
  } else {
    notInCV.push(skill);
  }
}

for (const s of inCV)    console.log(`  \x1b[32m✅ ${s}\x1b[0m`);
for (const s of notInCV) console.log(`  \x1b[31m❌ ${s}  ← in profile.yml but NOT in cv.md\x1b[0m`);

console.log(`\n── Result ───────────────────────────────────`);
console.log(`  Matched:   ${inCV.length}/${skills.length}`);

if (notInCV.length === 0) {
  console.log(`  \x1b[32mAll profile skills appear in your CV. ✓\x1b[0m\n`);
} else {
  console.log(`  \x1b[31m${notInCV.length} skill(s) in profile.yml are missing from cv.md\x1b[0m`);
  console.log(`\n  This means the AI will claim you have these skills during evaluation,`);
  console.log(`  but your actual CV won't mention them. Fix this before applying.\n`);
  console.log(`  Either:`);
  console.log(`    1. Add the skill to cv.md (if you genuinely have it)`);
  console.log(`    2. Remove it from profile.yml (if it was added by mistake)\n`);
}
