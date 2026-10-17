"""Use frozen Cycles reference optics with an explicitly bound numerical pose.
Only the data model factory is substituted inside this isolated Blender process;
lighting, shadow rays, camera, calibration and original source files are unchanged.
"""
from __future__ import annotations
import json,re,runpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'workbench'))
import model
from surface_model import PoseModel
from surface_registry import source_digest


def render_reference(ident):
    if not re.fullmatch(r's[56]-[a-f0-9]{24}',ident):raise ValueError('Invalid fixed render id')
    spec_path=model.CACHE/'specs'/(ident+'.json');spec=json.loads(spec_path.read_text())
    base=model.HeadModel();pose=PoseModel(base,spec['extraWeights'],spec['expression'])
    factory=model.HeadModel;argv=sys.argv[:]
    try:
        model.HeadModel=lambda:pose
        sys.argv=[str(ROOT/'workbench/study_reference.py'),'--',str(spec_path)]
        runpy.run_path(str(ROOT/'workbench/study_reference.py'),run_name='__main__')
    finally:model.HeadModel=factory;sys.argv=argv
    for arm in ('shadow','unshadowed'):
        path=model.CACHE/'studies/reference'/(ident+'-'+arm+'.json')
        meta=json.loads(path.read_text());meta['surfaceSourceDigest']=source_digest(spec['stage'])
        meta['identityHash']=pose.signature(spec['weights'])['identityHash'];meta['expression']=spec['expression']
        model.save_json(path,meta)
    print('SURFACE_REFERENCE_COMPLETE',ident,flush=True)


def main():
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    if len(args)==1:render_reference(args[0]);return
    if len(args)==2 and args[0]=='--case':
        from surface_registry import case
        case(args[1]);index=json.loads((model.CACHE/'surface/cases'/args[1]/'index.json').read_text())
        for ident in index['renderIds']:render_reference(ident)
        return
    raise SystemExit('Usage: surface_reference.py -- RENDER_ID | -- --case REGISTERED_CASE')
if __name__=='__main__':main()
