#!/usr/bin/env node
/**
 * scripts/instahyre.mjs — Instahyre.com REST API scanner
 * Quality Indian platform for tech/startup roles. No login needed.
 * Run: npm run scan:instahyre
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "..");
const sleep = ms => new Promise(r => setTimeout(r, ms));
const rand  = (a, b) => Math.floor(Math.random() * (b - a) + a);

function readConfig() {
  const text = fs.readFileSync(path.join(ROOT,"config/profile.yml"),"utf8");
  const roles=[], skills=[];
  let inR=false, inS=false;
  for(const line of text.split("\n")) {
    if(line.trim().startsWith("target_roles:")) {inR=true;inS=false;continue;}
    if(line.trim().startsWith("skills:"))       {inS=true;inR=false;continue;}
    if(inR && line.match(/^ {4}- /)) roles.push(line.replace(/^ {4}- /,"").trim());
    else if(inR && !line.match(/^ {4}/)) inR=false;
    if(inS && line.match(/^ {4}- /)) skills.push(line.replace(/^ {4}- /,"").trim());
    else if(inS && !line.match(/^ {4}/)) inS=false;
  }
  return {roles,skills};
}
const NOISE=["senior director","vp ","vice president","head of","devops","qa engineer",
  "android developer","ios developer"];
function isMatch(title,roles){const t=title.toLowerCase();
  if(NOISE.some(n=>t.includes(n))) return false;
  return roles.some(r=>{const rl=r.toLowerCase();
    return t.includes(rl)||rl.split(" ").some(w=>w.length>4&&t.includes(w));});}
async function fetchPage(query,skills,page){
  const qs=new URLSearchParams({format:"json",page,designation__icontains:query,
    profile__skills__name__in:skills.slice(0,5).join(","),
    min_experience:0,max_experience:3,
    location__in:"Bangalore,Hyderabad,Mumbai,Delhi,Pune,Chennai,Remote"});
  try{
    const res=await fetch(`https://www.instahyre.com/api/v1/opportunity/?${qs}`,{
      headers:{"User-Agent":"Mozilla/5.0","Accept":"application/json",
        "Referer":"https://www.instahyre.com/jobs/","X-Requested-With":"XMLHttpRequest"},
      signal:AbortSignal.timeout(15000)});
    if(!res.ok) return null;
    return await res.json();
  }catch{return null;}
}
function norm(raw){
  const co=raw.company?.name||raw.employer?.company_name||"";
  const loc=Array.isArray(raw.location)?raw.location.map(l=>l.name||l).join(", "):(raw.location||"");
  const sal=raw.min_salary&&raw.max_salary
    ?`${Math.round(raw.min_salary/100000)}–${Math.round(raw.max_salary/100000)} LPA`:"Not disclosed";
  return{source:"instahyre",company:co,tier:"unknown",title:raw.designation||"",location:loc,salary:sal,
    url:`https://www.instahyre.com/jobs/${raw.id}/`,posted_at:raw.created_at||"",
    remote:loc.toLowerCase().includes("remote"),snippet:(raw.description||"").slice(0,300)};}
const {roles,skills}=readConfig();
const queries=[...new Set([...roles,"data analyst","analytics","business analyst","SQL Python"])];
const allJobs=[],seen=new Set();
console.log("\n📍 Instahyre scanner (REST API — no login)\n");
for(const q of queries){
  process.stdout.write(`  "${q}"...`);
  let found=0;
  for(let p=1;p<=3;p++){
    const data=await fetchPage(q,skills,p);
    if(!data?.results?.length) break;
    for(const raw of data.results){
      const job=norm(raw);if(!isMatch(job.title,roles)) continue;
      const key=`${job.title.toLowerCase()}|${job.company.toLowerCase()}`;
      if(seen.has(key)) continue;
      seen.add(key);allJobs.push(job);found++;
    }
    if(!data.next) break;
    await sleep(rand(2000,4000));
  }
  console.log(` ${found} new`);
  await sleep(rand(2500,5000));
}
const scanPath=path.join(ROOT,"data/scan_results.json");
let existing={jobs:[]};
try{existing=JSON.parse(fs.readFileSync(scanPath,"utf8"));}catch{}
const combined=[...existing.jobs.filter(j=>j.source!=="instahyre"),...allJobs];
fs.mkdirSync(path.join(ROOT,"data"),{recursive:true});
fs.writeFileSync(scanPath,JSON.stringify({scanned_at:new Date().toISOString(),total:combined.length,jobs:combined},null,2));
console.log(`\n${"─".repeat(50)}`);
console.log(`✅ Instahyre: ${allJobs.length} jobs | Total: ${combined.length}`);
if(allJobs.length>0){console.log();
  allJobs.slice(0,5).forEach((j,i)=>console.log(`  ${i+1}. ${j.company.padEnd(20)} ${j.title}\n     ${j.location} | ${j.salary}\n     ${j.url}\n`));}
