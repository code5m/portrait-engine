#!/usr/bin/env node
/** Offline anonymous aggregation: node scripts/analyze-r010.mjs path/file.json [more...] */
import { readFile, readdir, stat, writeFile } from 'node:fs/promises';
import { resolve, extname, join } from 'node:path';
import { summarize } from '../src/blind010.mjs';

async function collect(args) {
  const paths=[];
  for (const arg of args) {
    const p=resolve(arg);
    const info=await stat(p);
    if (info.isDirectory()) {
      for (const name of (await readdir(p)).sort()) if (extname(name).toLowerCase()==='.json') paths.push(join(p,name));
    } else if (info.isFile()) paths.push(p);
  }
  return paths;
}

async function main() {
  const args=process.argv.slice(2);
  if (!args.length || args.includes('--help')) {
    console.log('Usage: node scripts/analyze-r010.mjs INPUT.json [INPUT.json | DIRECTORY ...] [--out summary.json]');
    return;
  }
  const outIndex=args.indexOf('--out');
  const out=outIndex>=0?args[outIndex+1]:null;
  if (outIndex>=0 && (!out || out.startsWith('--'))) throw new Error('--out requires a filename');
  if (outIndex>=0) args.splice(outIndex,2);
  const paths=await collect(args);
  if (paths.length>500) throw new Error('At most 500 ratings at once');
  const data=[];
  for (const path of paths) {
    const info=await stat(path);
    if (info.size>128*1024) { data.push({rejectedInputTooLarge:true}); continue; }
    try {data.push(JSON.parse(await readFile(path,'utf8')));}
    catch {data.push({unparseableJSON:true});}
  }
  const summary=summarize(data);
  const json=JSON.stringify(summary,null,2)+'\n';
  if (out) await writeFile(resolve(out),json,'utf8');
  process.stdout.write(json);
}
main().catch(e=>{console.error('Cannot analyze study data: '+e.message);process.exitCode=1;});
