#!/usr/bin/env node
/**
 * scripts/scan.mjs — career-ops-india portal scanner
 * 
 * Hits Greenhouse, Lever, and Ashby ATS APIs for 60+ Indian companies.
 * Zero LLM tokens. Zero scraping. Clean JSON responses.
 * 
 * Run:  npm run scan
 * Run:  node scripts/scan.mjs --board greenhouse
 * Run:  node scripts/scan.mjs --json    (raw JSON output)
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "..");

// ── Minimal YAML config reader ────────────────────────────────────────────────
function readConfig() {
  const p = path.join(ROOT, "config/profile.yml");
  if (!fs.existsSync(p)) {
    console.error("❌ config/profile.yml not found. Run: npm run doctor");
    process.exit(1);
  }
  const text = fs.readFileSync(p, "utf8");
  const roles = [];
  let inRoles = false;
  for (const line of text.split("\n")) {
    if (line.trim().startsWith("target_roles:")) { inRoles = true; continue; }
    if (inRoles && line.match(/^\s{4}- /)) roles.push(line.replace(/^\s{4}- /, "").trim());
    else if (inRoles && !line.match(/^\s{4}/)) inRoles = false;
  }
  const expMatch = text.match(/experience_years:\s*([\d.]+)/);
  const expYears = expMatch ? parseFloat(expMatch[1]) : 2;
  return { roles, expYears };
}

// ── Portals loader ────────────────────────────────────────────────────────────
function readPortals() {
  const p = path.join(ROOT, "portals/india.yml");
  const text = fs.readFileSync(p, "utf8");
  const result = { greenhouse: [], lever: [], ashby: [] };
  let section = null, current = null;
  for (const line of text.split("\n")) {
    if (line.startsWith("#") || !line.trim()) continue;
    const indent = line.match(/^(\s*)/)[1].length;
    const content = line.trim();
    if (indent === 0 && content.endsWith(":")) { section = content.replace(":",""); continue; }
    if (indent === 2 && content.startsWith("- name:")) {
      current = { name: content.replace("- name:","").trim() };
      if (result[section]) result[section].push(current);
    } else if (indent === 4 && current) {
      const [k,...v] = content.split(":");
      current[k.trim()] = v.join(":").trim();
    }
  }
  return result;
}

// ── ATS fetchers ──────────────────────────────────────────────────────────────
async function fetchGreenhouse(slug) {
  try {
    const res = await fetch(`https://boards-api.greenhouse.io/v1/boards/${slug}/jobs?content=true`,
      { headers: { "User-Agent": "career-ops-india/1.0" }, signal: AbortSignal.timeout(12000) });
    if (!res.ok) return { jobs: [], err: `HTTP ${res.status}` };
    const d = await res.json();
    return { jobs: d.jobs || [] };
  } catch(e) { return { jobs: [], err: e.message }; }
}

async function fetchLever(slug) {
  try {
    const res = await fetch(`https://api.lever.co/v0/postings/${slug}?mode=json`,
      { headers: { "User-Agent": "career-ops-india/1.0" }, signal: AbortSignal.timeout(12000) });
    if (!res.ok) return { jobs: [], err: `HTTP ${res.status}` };
    const d = await res.json();
    return { jobs: Array.isArray(d) ? d : [] };
  } catch(e) { return { jobs: [], err: e.message }; }
}

async function fetchAshby(slug) {
  try {
    const res = await fetch(`https://api.ashbyhq.com/posting-api/job-board/${slug}`,
      { headers: { "User-Agent": "career-ops-india/1.0", "Accept": "application/json" },
        signal: AbortSignal.timeout(12000) });
    if (!res.ok) return { jobs: [], err: `HTTP ${res.status}` };
    const d = await res.json();
    return { jobs: d.jobPostings || [] };
  } catch(e) { return { jobs: [], err: e.message }; }
}

// ── Normalizers ───────────────────────────────────────────────────────────────
function normGH(j, co) {
  return { source:"greenhouse", company:co.name, tier:co.tier||"2",
    title:j.title||"", location:j.location?.name||"India",
    url:j.absolute_url||`https://boards.greenhouse.io/${co.slug}/jobs/${j.id}`,
    posted_at:j.updated_at||j.created_at||null, department:j.departments?.[0]?.name||"",
    remote:(j.location?.name||"").toLowerCase().includes("remote"),
    snippet:(j.content||"").replace(/<[^>]*>/g," ").slice(0,300) };
}
function normLV(j, co) {
  const loc = j.categories?.location || j.workplaceType || "";
  return { source:"lever", company:co.name, tier:co.tier||"2",
    title:j.text||"", location:loc,
    url:j.hostedUrl||j.applyUrl||"",
    posted_at:j.createdAt ? new Date(j.createdAt).toISOString() : null,
    department:j.categories?.department||"",
    remote:loc.toLowerCase().includes("remote"),
    snippet:(j.descriptionPlain||"").slice(0,300) };
}
function normAB(j, co) {
  const loc = j.locationName||j.jobPostingLocations?.[0]?.locationName||"";
  return { source:"ashby", company:co.name, tier:co.tier||"2",
    title:j.title||"", location:loc,
    url:`https://jobs.ashbyhq.com/${co.slug}/${j.id}`,
    posted_at:j.publishedAt||null, department:j.departmentName||"",
    remote:j.isRemote||loc.toLowerCase().includes("remote"),
    snippet:(j.descriptionHtml||"").replace(/<[^>]*>/g," ").slice(0,300) };
}

// ── Matcher ───────────────────────────────────────────────────────────────────
const DATA_KEYWORDS = ["data","analytics","analyst","business intelligence","sql",
  "python","bi","product analyst","insights","dashboard","reporting","etl","pipeline"];
const NOISE_TERMS = ["senior director","vp ","vice president","head of","principal ",
  "staff engineer","c++","android developer","ios developer","frontend developer",
  "backend developer","devops","qa engineer","sdet","mobile developer"];

function matches(job, roles, maxExp) {
  const t = job.title.toLowerCase();
  const c = job.snippet.toLowerCase();
  const loc = job.location.toLowerCase();
  const titleMatch = roles.some(r => t.includes(r.toLowerCase()) ||
    r.toLowerCase().split(" ").some(w => w.length > 4 && t.includes(w)));
  const kwMatch = !titleMatch && DATA_KEYWORDS.filter(k => c.includes(k)).length >= 3;
  const locMatch = job.remote || !job.location || loc.includes("india") ||
    ["bangalore","hyderabad","mumbai","delhi","pune","chennai","gurgaon","noida","remote"]
      .some(l => loc.includes(l));
  const noNoise = !NOISE_TERMS.some(n => t.includes(n));
  return (titleMatch || kwMatch) && locMatch && noNoise;
}

// ── Main ──────────────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const boardFilter = args.find(a => a.startsWith("--board="))?.split("=")[1];
const jsonMode = args.includes("--json");

const { roles, expYears } = readConfig();
const portals = readPortals();
const results = [], errors = [];

if (!jsonMode) {
  console.log(`\n🔍 career-ops-india scanner`);
  console.log(`   Roles: ${roles.join(", ")}`);
  console.log(`   Companies: ${portals.greenhouse.length + portals.lever.length + portals.ashby.length}\n`);
}

async function scanBoard(name, companies, fetcher, normalizer) {
  if (boardFilter && boardFilter !== name) return;
  if (!jsonMode) process.stdout.write(`Scanning ${companies.length} ${name} companies...`);
  const tasks = companies.map(async co => {
    if (co.note?.includes("current employer")) return;
    const { jobs, err } = await fetcher(co.slug);
    if (err) { errors.push({ company: co.name, error: err }); return; }
    const matched = jobs.map(j => normalizer(j, co)).filter(j => matches(j, roles, expYears));
    if (matched.length && !jsonMode) process.stdout.write(` ${co.name}(${matched.length})`);
    results.push(...matched);
  });
  await Promise.allSettled(tasks);
  if (!jsonMode) console.log(" ✓");
}

await scanBoard("greenhouse", portals.greenhouse, fetchGreenhouse, normGH);
await scanBoard("lever",      portals.lever,      fetchLever,      normLV);
await scanBoard("ashby",      portals.ashby,      fetchAshby,      normAB);

// Dedup by title+company
const seen = new Set();
const unique = results.filter(j => {
  const key = `${j.title.toLowerCase().trim()}|${j.company.toLowerCase().trim()}`;
  if (seen.has(key)) return false;
  seen.add(key); return true;
});

// Sort: tier 1 first, then by source
unique.sort((a,b) => (a.tier === "1" ? -1 : 1) - (b.tier === "1" ? -1 : 1));

// Save
const dataDir = path.join(ROOT, "data");
fs.mkdirSync(dataDir, { recursive: true });
const out = { scanned_at: new Date().toISOString(), total: unique.length,
              errors: errors.length, jobs: unique };
fs.writeFileSync(path.join(dataDir, "scan_results.json"), JSON.stringify(out, null, 2));

if (jsonMode) { console.log(JSON.stringify(out)); process.exit(0); }

console.log(`\n${"─".repeat(50)}`);
console.log(`✅ ${unique.length} matching jobs found  |  ⚠️  ${errors.length} companies unreachable`);
console.log(`${"─".repeat(50)}\n`);

if (unique.length === 0) {
  console.log("No matches found. Try broadening your target roles in config/profile.yml.\n");
  process.exit(0);
}

const tier1 = unique.filter(j => j.tier === "1");
const tier2 = unique.filter(j => j.tier !== "1");

if (tier1.length) {
  console.log(`🏆 Tier 1 companies (${tier1.length} matches):`);
  tier1.slice(0,10).forEach((j,i) =>
    console.log(`  ${i+1}. ${j.company.padEnd(20)} ${j.title}\n     📍 ${j.location||"India"}  🔗 ${j.url}`));
  if (tier1.length > 10) console.log(`  ... and ${tier1.length-10} more`);
}

if (tier2.length) {
  console.log(`\n📋 Other matches (${tier2.length}):`);
  tier2.slice(0,10).forEach((j,i) =>
    console.log(`  ${i+1}. ${j.company.padEnd(20)} ${j.title}\n     📍 ${j.location||"India"}  🔗 ${j.url}`));
  if (tier2.length > 10) console.log(`  ... and ${tier2.length-10} more`);
}

console.log(`\n💾 Full list saved to data/scan_results.json`);
console.log(`\nNext steps:`);
console.log(`  → Open Claude Code or Gemini CLI in this folder`);
console.log(`  → /evaluate [any URL above]  to get a full A–F score\n`);
