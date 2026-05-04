#!/usr/bin/env node
/**
 * scripts/verify-pipeline.mjs
 *
 * Validates data/pipeline.json for integrity issues.
 * Run: npm run verify
 *
 * Catches: corrupt JSON, missing required fields, invalid status values,
 * duplicate IDs, future dates, status logic errors.
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "..");
const PIPELINE_PATH = path.join(ROOT, "data/pipeline.json");

const VALID_STATUSES = [
  "to_apply", "applied", "hr_screen", "technical",
  "final_round", "offer", "accepted", "rejected", "withdrawn", "expired"
];

const REQUIRED_FIELDS = ["id", "company", "role", "status", "date_found"];

let issues = 0;
let warnings = 0;

function err(msg)  { console.log(`  \x1b[31m❌ ${msg}\x1b[0m`); issues++; }
function warn(msg) { console.log(`  \x1b[33m⚠️  ${msg}\x1b[0m`); warnings++; }
function ok(msg)   { console.log(`  \x1b[32m✅ ${msg}\x1b[0m`); }

console.log(`\n\x1b[1mPipeline Integrity Check\x1b[0m\n`);

// ── File existence ─────────────────────────────────────────────────────────────
if (!fs.existsSync(PIPELINE_PATH)) {
  console.log("No pipeline.json found. Creating empty file.");
  fs.writeFileSync(PIPELINE_PATH, "[]");
  process.exit(0);
}

// ── JSON validity ─────────────────────────────────────────────────────────────
let pipeline;
try {
  pipeline = JSON.parse(fs.readFileSync(PIPELINE_PATH, "utf8"));
  ok(`Valid JSON — ${pipeline.length} entries`);
} catch (e) {
  err(`pipeline.json is corrupted: ${e.message}`);
  console.log(`\n  Try: Open data/pipeline.json in a text editor and fix the JSON syntax.`);
  console.log(`  Or:  Restore from your last git commit: git checkout data/pipeline.json\n`);
  process.exit(1);
}

if (!Array.isArray(pipeline)) {
  err("pipeline.json must be a JSON array [ ... ]");
  process.exit(1);
}

if (pipeline.length === 0) {
  console.log("  Pipeline is empty — nothing to validate.\n");
  process.exit(0);
}

// ── Per-entry validation ──────────────────────────────────────────────────────
const seenIds = new Set();
const today = new Date();

for (let i = 0; i < pipeline.length; i++) {
  const entry = pipeline[i];
  const label = `Entry ${i + 1} (${entry.company || "unknown"} — ${entry.role || "unknown"})`;

  // Required fields
  for (const field of REQUIRED_FIELDS) {
    if (!entry[field]) {
      err(`${label}: missing required field "${field}"`);
    }
  }

  // ID uniqueness
  if (entry.id) {
    if (seenIds.has(entry.id)) {
      err(`${label}: duplicate ID "${entry.id}" — run: npm run dedup`);
    } else {
      seenIds.add(entry.id);
    }
  }

  // Status validity
  if (entry.status && !VALID_STATUSES.includes(entry.status)) {
    err(`${label}: invalid status "${entry.status}". Valid: ${VALID_STATUSES.join(", ")}`);
  }

  // Date sanity
  if (entry.date_found) {
    const found = new Date(entry.date_found);
    if (isNaN(found.getTime())) {
      err(`${label}: invalid date_found "${entry.date_found}"`);
    } else if (found > today) {
      warn(`${label}: date_found is in the future`);
    }
  }

  if (entry.date_applied && entry.date_found) {
    const applied = new Date(entry.date_applied);
    const found   = new Date(entry.date_found);
    if (applied < found) {
      warn(`${label}: date_applied is before date_found — check dates`);
    }
  }

  // Status logic
  if (entry.status === "applied" && !entry.date_applied) {
    warn(`${label}: status is "applied" but date_applied is not set`);
  }

  if (["hr_screen", "technical", "final_round", "offer"].includes(entry.status) && !entry.date_applied) {
    warn(`${label}: status is "${entry.status}" but never marked as applied`);
  }

  // Stale check
  if (entry.status === "applied" && entry.date_applied) {
    const daysSinceApplied = Math.floor((today - new Date(entry.date_applied)) / 86400000);
    if (daysSinceApplied > 30) {
      warn(`${label}: applied ${daysSinceApplied} days ago with no update — consider marking as ghosted`);
    }
  }

  // URL check
  if (!entry.url) {
    warn(`${label}: no URL set — can't run liveness check`);
  }
}

// ── Summary ───────────────────────────────────────────────────────────────────
const byStatus = {};
for (const entry of pipeline) {
  byStatus[entry.status] = (byStatus[entry.status] || 0) + 1;
}

console.log(`\n\x1b[1m── Pipeline Summary\x1b[0m`);
for (const [status, count] of Object.entries(byStatus)) {
  console.log(`  ${status.padEnd(15)} ${count}`);
}

console.log(`\n\x1b[1m── Integrity Result\x1b[0m`);
if (issues === 0 && warnings === 0) {
  ok("Pipeline data is clean.");
} else {
  if (issues > 0)   console.log(`  \x1b[31m❌ ${issues} error(s) found\x1b[0m`);
  if (warnings > 0) console.log(`  \x1b[33m⚠️  ${warnings} warning(s)\x1b[0m`);
}
console.log();
