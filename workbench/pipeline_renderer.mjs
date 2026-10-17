import {draw as drawStudy} from './study_renderer.mjs';
import {draw as drawSurface} from './surface_renderer.mjs';
export function draw(target,descriptor,mode='tone') {
  return ['S5','S6'].includes(descriptor.stage)?drawSurface(target,descriptor,mode):drawStudy(target,descriptor,mode);
}
