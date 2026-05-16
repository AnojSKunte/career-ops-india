#!/usr/bin/env node
/**
 * scripts/cutshort.mjs — Cutshort.io job scraper
 * Indian startup job platform, skills-based matching.
 * Run: npm run scan:cutshort
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
const NOISE=["senior director","vp ","vice president","head of","devops","qa engineer",
  "android developer","ios developer","frontend developer","backend developer"];
function isMatch(title,roles){
  const t=title.toLowerCase();
  if(NOISE.some(n=>t.includes(n))) return false;
  return roles.some(r=>{const rl=r.toLowerCase();
    return t.includes(rl)||rl.split(" ").some(w=>w.length>4&&t.includes(w));});}
async function search(query,page){
  const body={data:{title:query,skills:[],
    locations:["Bangalore","Hyderabad","Mumbai","Delhi","Pune","Chennai","Remote"],
    experience:{min:0,max:3},equity:false},page,limit:20};
  try{
    const res=await fetch("https://cutshort.io/api/web/jobs/search",{
      method:"POST",
      headers:{"Content-Type":"application/json","Accept":"application/json",
        "User-Agent":"Mozilla/5.0","Referer":"https://cutshort.io/jobs","Origin":"https://cutshort.io"},
      body:JSON.stringify(body),signal:AbortSignal.timeout(15000)});
    if(!res.ok) return null;
    return await res.json();
  }catch{return null;}
}
function norm(raw){
  const co=raw.company?.name||"";
  const loc=Array.isArray(raw.locations)?raw.locations.join(", "):(raw.location||"");
  const minC=raw.minCTC?Math.round(raw.minCTC/100000):null;
  const maxC=raw.maxCTC?Math.round(raw.maxCTC/100000):null;
  const sal=minC&&maxC?`${minC}–${maxC} LPA`:"Not disclosed";
  const slug=raw.shortUrl||raw.jobId||raw.id;
  return{source:"cutshort",company:co,tier:"unknown",title:raw.title||raw.designation||"",
    location:loc,salary:sal,url:slug?`https://cutshort.io/job/${slug}`:"https://cutshort.io/jobs",
    posted_at:raw.postedAt||raw.createdAt||"",remote:loc.toLowerCase().includes("remote"),
    snippet:(raw.about||raw.description||"").slice(0,300)};}
const roles=readRoles();
const queries=[...new Set([...roles,"data analyst","analytics engineer","business analyst","product analyst"])];
const allJobs=[],seen=new Set();
console.log("\n✂️  Cutshort scanner (startup roles — skills-based)\n");
for(const q of queries){
  process.stdout.write(`  "${q}"...`);
  let found=0;
  for(let p=1;p<=3;p++){
    const data=await search(q,p);
    if(!data?.data?.jobs?.length) break;
    for(const raw of data.data.jobs){
      const job=norm(raw);if(!isMatch(job.title,roles)) continue;
      const key=`${job.title.toLowerCase()}|${job.company.toLowerCase()}`;
      if(seen.has(key)) continue;
      seen.add(key);allJobs.push(job);found++;
    }
    if(!data.data.hasMore) break;
    await sleep(rand(2000,4000));
  }
  console.log(` ${found} new`);
  await sleep(rand(2500,5000));
}
const scanPath=path.join(ROOT,"data/scan_results.json");
let existing={jobs:[]};
try{existing=JSON.parse(fs.readFileSync(scanPath,"utf8"));}catch{}
const combined=[...existing.jobs.filter(j=>j.source!=="cutshort"),...allJobs];
fs.mkdirSync(path.join(ROOT,"data"),{recursive:true});
fs.writeFileSync(scanPath,JSON.stringify({scanned_at:new Date().toISOString(),total:combined.length,jobs:combined},null,2));
console.log(`\n${"─".repeat(50)}`);
console.log(`✅ Cutshort: ${allJobs.length} jobs | Total: ${combined.length}`);
if(allJobs.length>0){console.log();
  allJobs.slice(0,5).forEach((j,i)=>console.log(`  ${i+1}. ${j.company.padEnd(20)} ${j.title}\n     ${j.location} | ${j.salary}\n     ${j.url}\n`));}
