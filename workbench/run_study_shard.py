"""Run one explicitly selected, frozen identity through an unchanged study.

This only partitions execution; it never edits the on-disk protocol, weights,
lights, thresholds or result rows. The CI matrix covers every registered identity
and its all-scenes gate requires every shard. No arbitrary script/path input.
"""
from __future__ import annotations
import json,runpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PHASES={'compile':'study_light.py','reference':'study_reference.py','validate':'validate_studies.py'}


def select_identity(config,identity_id):
    matches=[x for x in config['identities'] if x['id']==identity_id]
    if len(matches)!=1:raise ValueError('Expected exactly one registered identity')
    identity=matches[0]
    if identity['split'] not in ('baseline','holdout'):raise ValueError('Unregistered split')
    return identity


def main():
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    if len(args)!=2 or args[0] not in PHASES:raise SystemExit('Usage: run_study_shard.py compile|reference|validate REGISTERED_IDENTITY')
    phase,identity_id=args
    import model
    original=model.CONFIG
    identity=select_identity(original,identity_id)
    print('FROZEN_STUDY_SHARD '+json.dumps({'phase':phase,'identity':identity_id,'split':identity['split'],
          'registeredIdentities':[x['id'] for x in original['identities']],
          'lights':[x['id'] for x in original['lights']]}),flush=True)
    # Module imports in the target receive a run-local cohort selection. All
    # source digests still hash the complete original protocol bytes on disk.
    model.CONFIG={**original,'identities':[identity]}
    script=ROOT/'workbench'/PHASES[phase]
    sys.argv=[str(script),'--',identity['split']] if phase=='reference' else [str(script),identity['split']]
    runpy.run_path(str(script),run_name='__main__')
if __name__=='__main__':main()
