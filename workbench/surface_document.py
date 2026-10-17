"""Self-contained native CSS export, preserving MIT attribution in its descriptor."""
import json
from model import ROOT,canonical


def document(descriptor,mode='tone'):
    if mode not in ('tone','structure','masses','edges-control','material-control','hair-control'):raise ValueError('Unknown export mode')
    base=(ROOT/'workbench/renderer.mjs').read_text().replace('export function','function')
    study=(ROOT/'workbench/study_renderer.mjs').read_text().replace("import {draw as drawBase, clipPath} from './renderer.mjs';",'const {draw:drawBase,clipPath}=Base;').replace('export function','function')
    surface=(ROOT/'workbench/surface_renderer.mjs').read_text().replace("import {draw as drawStudy,edgeClipPath} from './study_renderer.mjs';",'const {draw:drawStudy,edgeClipPath}=Study;').replace('export function','function')
    data=canonical(descriptor).decode().replace('<','\\u003c')
    return ('<!doctype html><meta charset="utf-8"><title>CSS surface study</title><style>'
            'body{margin:0}.portrait{position:relative;width:320px;height:320px;background:white;overflow:hidden}'
            '.tone-region{position:absolute;inset:0;display:block}</style><div id="portrait" class="portrait"></div><script>'
            'const Base=(()=>{'+base+';return {draw,clipPath};})();'
            'const Study=(()=>{'+study+';return {draw,edgeClipPath};})();'+surface+
            '\ndraw(document.getElementById("portrait"),'+data+','+json.dumps(mode)+');document.body.dataset.ready="1";</script>')
