"""Compile every predeclared case; no selection using measured pictures."""
from __future__ import annotations
import json,sys,time
from model import CACHE,HeadModel,canonical,save_json
from geometry import Projection
from surface_model import PoseModel
from surface_registry import case,case_specs,sample_id,source_digest
from surface import prepare_geometry
from surface_service import render


def compile_case(case_id):
    c=case(case_id);specs=case_specs(case_id);base=HeadModel();first=specs[0]
    pose=PoseModel(base,first['extraWeights'],first['expression']);projection=Projection(pose,first['weights'])
    geometry=prepare_geometry(projection);ids=[];alternatives={};start=time.monotonic()
    for spec in specs:
        result=render(spec,base,pose,projection,geometry);ident=result['renderId'];ids.append(ident)
        variants={'alternate-material':{**spec,'material':'charcoal'},'no-hair':{**spec,'hair':'none'},'short-hair':{**spec,'hair':'short'}}
        alternatives[ident]={name:render(value,base,pose,projection,geometry)['renderId'] for name,value in variants.items()}
        print('SURFACE_COMPILED',sample_id(spec),ident,round(time.monotonic()-start,2),flush=True)
    save_json(CACHE/'surface/cases'/case_id/'index.json',{'caseId':case_id,'stage':c['stage'],'renderIds':ids,'alternatives':alternatives,'sourceDigest':source_digest(c['stage'])})


def main():
    if len(sys.argv)!=3:raise SystemExit('Usage: run_surface_matrix.py compile|validate|pack REGISTERED_CASE')
    action,case_id=sys.argv[1:];case(case_id)
    if action=='compile':compile_case(case_id)
    elif action=='validate':
        from surface_validate import run_case
        run_case(case_id)
    elif action=='pack':
        from archive_surface import pack
        pack(case_id)
    else:raise ValueError('Unknown surface phase')
if __name__=='__main__':main()
