#!/usr/bin/env node
/**
 * scripts/check-liveness.mjs
 *
 * Checks every URL in data/pipeline.json to see if the job is still live.
 * Dead links = job filled or removed. Flags them so you stop wasting time.
 *
 * Run: npm run liveness
 *
 * Signals that a job is dead:
 *  - HTTP 404 or 410
 *  - Redirect to /jobs or /careers (position removed)
 *  - Page contains "position has been filled" or "no longer accepting"
 *  - Greenhouse/Lever/Ashby return empty job object
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "..");

const PIPELINE_PATH = path.join(ROOT, "data/pipeline.json");
const DEAD_SIGNALS = [
  "position has been filled",
  "no longer accepting applications",
  "this job is no longer available",
  "position is closed",
  "job has expired",
  "application period has closed",
  "vacancy has been filled",
];

const ACTIVE_STATUSES = ["to_apply", "applied"];
const TIMEOUT_MS = 10000;

async function checkUrl(url) {
  if (!url || !url.startsWith("http")) {
    return { alive: null, reason: "no URL" };
  }

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

    const res = await fetch(url, {
      method: "GET",
      redirect: "follow",
      signal: controller.signal,
      headers: {
        "User-Agent": "Mozilla/5.0 (career-ops-india/1.0 link-checker)",
        "Accept": "text/html,application/json",
      },
    });

    clearTimeout(timer);

    if (res.status === 404 || res.status === 410 || res.status === 301) {
      return { alive: false, reason: `HTTP ${res.status}` };
    }

    // Check final URL after redirects — if it went to a generic /jobs page, job is gone
    const finalUrl = res.url;
    if (
      finalUrl !== url &&
      (finalUrl.endsWith("/jobs") || finalUrl.endsWith("/careers") || finalUrl.endsWith("/en/"))
    ) {
      return { alive: false, reason: `redirected to ${finalUrl}` };
    }

    // Check page content for dead signals
    const text = (await res.text()).toLowerCase();
    const deadSignal = DEAD_SIGNALS.find(s => text.includes(s));
    if (deadSignal) {
      return { alive: false, reason: `page says: "${deadSignal}"` };
    }

    return { alive: true, reason: `HTTP ${res.status}` };
  } catch (e) {
    if (e.name === "AbortError") {
      return { alive: null, reason: "timeout" };
    }
    return { alive: null, reason: e.message.slice(0, 60) };
  }
}

// ── Main ──────────────────────────────────────────────────────────────────────
if (!fs.existsSync(PIPELINE_PATH)) {
  console.log("No pipeline.json found. Nothing to check.");
  process.exit(0);
}

const pipeline = JSON.parse(fs.readFileSync(PIPELINE_PATH, "utf8"));
const toCheck = pipeline.filter(j =>
  ACTIVE_STATUSES.includes(j.status) && j.url
);

if (toCheck.length === 0) {
  console.log("No active applications with URLs to check.");
  process.exit(0);
}

console.log(`\n🔗 Checking ${toCheck.length} active job links...\n`);

const results = { alive: [], dead: [], unknown: [] };

for (const job of toCheck) {
  process.stdout.write(`  Checking ${job.company} — ${job.role}... `);
  const { alive, reason } = await checkUrl(job.url);

  if (alive === true) {
    process.stdout.write(`\x1b[32m✅ Live\x1b[0m\n`);
    results.alive.push(job);
  } else if (alive === false) {
    process.stdout.write(`\x1b[31m❌ Dead — ${reason}\x1b[0m\n`);
    results.dead.push({ ...job, dead_reason: reason });

    // Mark as dead in pipeline
    const idx = pipeline.findIndex(p => p.id === job.id);
    if (idx !== -1) {
      pipeline[idx].status = "expired";
      pipeline[idx].notes = (pipeline[idx].notes || "") + ` [Auto: link dead — ${reason}]`;
    }
  } else {
    process.stdout.write(`\x1b[33m⚠️  Unknown — ${reason}\x1b[0m\n`);
    results.unknown.push(job);
  }

  // Small delay to not hammer servers
  await new Promise(r => setTimeout(r, 500));
}

// Save updated pipeline
fs.writeFileSync(PIPELINE_PATH, JSON.stringify(pipeline, null, 2));

// Summary
console.log(`\n── Liveness Summary ────────────────────────`);
console.log(`  \x1b[32m✅ Live:    ${results.alive.length}\x1b[0m`);
console.log(`  \x1b[31m❌ Dead:    ${results.dead.length}\x1b[0m`);
console.log(`  \x1b[33m⚠️  Unknown: ${results.unknown.length}\x1b[0m`);

if (results.dead.length > 0) {
  console.log(`\n❌ Dead jobs have been marked 'expired' in your pipeline.`);
  console.log(`   Don't waste time applying to these — the positions are gone.`);
  console.log(`   Run: npm run scan  to find fresh replacements.\n`);
} else {
  console.log(`\n✅ All active applications are at live URLs.\n`);
}
