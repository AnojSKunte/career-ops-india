#!/usr/bin/env node
/**
 * scripts/wellfound.mjs — Wellfound (AngelList) India jobs scraper
 * Best source for funded global startup roles with India filter.
 * Run: npm run scan:wellfound
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "..");
const sleep = ms => new Promise(r => setTimeout(r, ms));
const rand  = (a, b) => Math.floor(Math.random() * (b - a) + a);

function readRoles(){
  const text=fs.readFileSync(path.join(ROOT,"config/profile.yml"),"utf8");
  const roles=[];let inR=false;
  for(const line of text.split("\n")){
    if(line.trim().startsWith("target_roles:")) {inR=true;continue;}
    if(inR && line.match(/^ {4}- /)) roles.push(line.replace(/^ {4}- /,"").trim());
    else if(inR && !line.match(/^ {4}/)) inR=false;
  }
  return roles;
}
const ROLE_SLUGS={"Data Analyst":"data-analyst","Analytics Engineer":"analytics",
  "Business Analyst":"business-analyst","Product Analyst":"product-analyst"};
const NOISE=["senior director","vp ","vice president","head of","devops","qa engineer"];
function isMatch(title,roles){
  const t=title.toLowerCase();
  if(NOISE.some(n=>t.includes(n))) return false;
  return roles.some(r=>{const rl=r.toLowerCase();
    return t.includes(rl)||rl.split(" ").some(w=>w.length>4&&t.includes(w));});}
async function fetchPage(slug,page){
  const url=`https://wellfound.com/role/l/${slug}/india?page=${page}`;
  try{
    const res=await fetch(url,{headers:{
      "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
      "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language":"en-IN,en;q=0.9"},signal:AbortSignal.timeout(15000)});
    if(!res.ok) return "";
    return await res.text();
  }catch{return "";}
}
function parse(html){
  const jobs=[];
  const match=html.match(/<script id="__NEXT_DATA__" type="application\/json">([^<]+)<\/script>/);
  if(!match) return jobs;
  try{
    const data=JSON.parse(match[1]);
    const pp=data?.props?.pageProps;
    const raw=pp?.jobListings||pp?.startupRoles||pp?.filteredStartupRoles||[];
    const listings=Array.isArray(raw)?raw:(raw?.startupRoles||raw?.edges?.map(e=>e.node)||[]);
    for(const j of listings){
      const title=j.title||j.role||"";
      const company=j.startup?.name||j.company?.name||j.organizationName||"";
      const loc=Array.isArray(j.locationNames)?j.locationNames.join(", "):(j.remote?"Remote":j.location||"India");
      const minS=j.compensation?.minCompensation;
      const maxS=j.compensation?.maxCompensation;
      const sal=minS?`${Math.round(minS/100000)}–${Math.round((maxS||minS*1.3)/100000)} LPA`:"Not disclosed";
      if(!title||!company) continue;
      jobs.push({source:"wellfound",company,tier:"1",title,location:loc,salary:sal,
        url:j.slug?`https://wellfound.com/jobs/${j.slug}`:"https://wellfound.com/jobs",
        posted_at:j.createdAt||"",remote:j.remote||loc.toLowerCase().includes("remote"),
        snippet:(j.description||"").slice(0,300)});
    }
  }catch{}
  return jobs;
}
const roles=readRoles();
const allJobs=[],seen=new Set();
console.log("\n🚀 Wellfound scanner (funded startups — India filter)\n");
for(const role of roles){
  const slug=ROLE_SLUGS[role]||role.toLowerCase().replace(/[^a-z0-9]+/g,"-");
  process.stdout.write(`  "${role}" → /${slug}/india...`);
  let found=0;
  for(let p=1;p<=3;p++){
    const html=await fetchPage(slug,p);if(!html) break;
    const jobs=parse(html).filter(j=>isMatch(j.title,roles));
    for(const job of jobs){
      const key=`${job.title.toLowerCase()}|${job.company.toLowerCase()}`;
      if(seen.has(key)) continue;
      seen.add(key);allJobs.push(job);found++;
    }
    if(jobs.length<8) break;
    await sleep(rand(3000,6000));
  }
  console.log(` ${found} new`);
  await sleep(rand(4000,7000));
}
const scanPath=path.join(ROOT,"data/scan_results.json");
let existing={jobs:[]};
try{existing=JSON.parse(fs.readFileSync(scanPath,"utf8"));}catch{}
const combined=[...existing.jobs.filter(j=>j.source!=="wellfound"),...allJobs];
fs.mkdirSync(path.join(ROOT,"data"),{recursive:true});
fs.writeFileSync(scanPath,JSON.stringify({scanned_at:new Date().toISOString(),total:combined.length,jobs:combined},null,2));
console.log(`\n${"─".repeat(50)}`);
console.log(`✅ Wellfound: ${allJobs.length} jobs | Total: ${combined.length}`);
if(allJobs.length>0){console.log();
  allJobs.slice(0,5).forEach((j,i)=>console.log(`  ${i+1}. ${j.company.padEnd(20)} ${j.title}\n     ${j.location} | ${j.salary}\n     ${j.url}\n`));}
