#!/usr/bin/env node
/**
 * scripts/dedup-tracker.mjs
 * Run: npm run dedup
 *
 * Removes duplicate applications — same company + role logged twice.
 * Keeps the entry with the most data (latest status, most notes).
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "..");
const PIPELINE_PATH = path.join(ROOT, "data/pipeline.json");

if (!fs.existsSync(PIPELINE_PATH)) {
  console.log("No pipeline.json found."); process.exit(0);
}

const pipeline = JSON.parse(fs.readFileSync(PIPELINE_PATH, "utf8"));
const before = pipeline.length;

// Status priority — keep the entry that's furthest along
const STATUS_PRIORITY = {
  "to_apply": 0, "applied": 1, "hr_screen": 2, "technical": 3,
  "final_round": 4, "offer": 5, "accepted": 6,
  "rejected": 2, "withdrawn": 2, "expired": 0,
};

const seen = new Map();

for (const entry of pipeline) {
  const key = `${entry.company?.toLowerCase().trim()}|${entry.role?.toLowerCase().trim()}`;
  if (!seen.has(key)) {
    seen.set(key, entry);
  } else {
    const existing = seen.get(key);
    const existingPriority = STATUS_PRIORITY[existing.status] ?? 0;
    const newPriority      = STATUS_PRIORITY[entry.status]    ?? 0;
    // Keep whichever has higher status, or more notes
    if (newPriority > existingPriority || 
        (newPriority === existingPriority && (entry.notes?.length || 0) > (existing.notes?.length || 0))) {
      seen.set(key, entry);
    }
  }
}

const deduped = Array.from(seen.values());
const removed = before - deduped.length;

if (removed === 0) {
  console.log(`✅ No duplicates found. Pipeline is clean (${before} entries).`);
} else {
  // Backup first
  fs.writeFileSync(PIPELINE_PATH + ".bak", JSON.stringify(pipeline, null, 2));
  fs.writeFileSync(PIPELINE_PATH, JSON.stringify(deduped, null, 2));
  console.log(`✅ Removed ${removed} duplicate(s). ${deduped.length} unique entries remain.`);
  console.log(`   Backup saved to data/pipeline.json.bak`);
}
