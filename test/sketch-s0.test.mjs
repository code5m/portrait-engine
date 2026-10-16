import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {unit,srgb,surfacePoint,radiance,bandContour,sceneMarkup} from '../study/sketch-s0.mjs';
const config=JSON.parse(fs.readFileSync(new URL('../research/sketch/s0-scenes.json',import.meta.url)));
test('S0 is a calibration instrument, never three human identities',()=>{
 assert.match(config.scope,/not a human/);assert.equal(config.profiles.length*config.lights.length,9);
});
test('vectors reject NaN and zero, linear light is not sRGB',()=>{
 assert.throws(()=>unit([0,0,0]));assert.throws(()=>unit([NaN,1,1]));
 assert.ok(Math.abs(srgb(.18)-.461356)<1e-5);
 assert.ok(Math.abs(Math.hypot(...unit([1,2,3]))-1)<1e-12);
});
test('inverse Gauss map lies on the ellipsoid with the requested normal',()=>{
 for(const r of config.profiles.map(x=>x.radii))for(const n of [[1,2,3],[-1,0,1],[0,1,0]]){
  const p=surfacePoint(n,r);assert.ok(Math.abs(p.reduce((s,x,i)=>s+(x/r[i])**2,0)-1)<1e-10);
  const actual=unit(p.map((x,i)=>x/r[i]**2));assert.ok(actual.every((x,i)=>Math.abs(x-unit(n)[i])<1e-10));
 }
});
test('terminator has zero DIRECT light, not a forced black outline',()=>{
 assert.equal(radiance([1,0,0],[0,0,1]),config.ambient);
 assert.equal(radiance([0,0,-1],[0,0,1]),config.ambient);
 assert.ok(Math.abs(radiance([0,0,1],[0,0,1])-.8)<1e-12);
});
test('one algorithm renders all nine shapes with a bounded CSS patch count',()=>{
 for(const p of config.profiles)for(const l of config.lights){
  const markup=sceneMarkup(config,p,l);assert.equal((markup.match(/<i /g)||[]).length,16);
  assert.doesNotMatch(markup,/NaN|Infinity|<img|<svg|<canvas|url\(/);
 }
 assert.notEqual(bandContour([1,1,1],[-1,0,1],.3),bandContour([1,1,1],[1,0,1],.3));
});
