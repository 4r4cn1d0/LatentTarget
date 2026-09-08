"""Join immutable pilot results and extension results, retaining all 720 cells."""
import argparse
from collections import Counter,defaultdict
import json
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from scripts.build_diagnostic_packet import rows
from scripts.audit_diagnostic_history_evidence import history_evidence
from src.diagnostic_pilot import read,file_sha,digest,write_new
from src.diagnostic_extension import validate_extension
from src.grounded_partner import descriptives,grounded_candidates,grounded_integrity
from src.stimulus_audit import SHALLOW,REFERENCES


def analyze(source,package,prior,new,output):
    manifest=read(source/'manifest.json')
    for name,sha in manifest['outputs'].items():
        if not (source/name).resolve().is_relative_to(source.resolve()) or file_sha(source/name)!=sha:
            raise ValueError('fixed source changed')
    packet=read(package/'extension_packet.json');pilot=read(package/'packet.json')
    sha=validate_extension(packet,pilot)
    plan=read(source/'design_snapshot.json');bank=read(source/'bank_snapshot.json')
    bundles=rows(source/'evaluation/bundles.jsonl.gz');ledger=rows(source/'evaluation/ledger.jsonl.gz')
    grounded_integrity(plan,bank,bundles,ledger)
    expected={r['request_id']:r for r in ledger if r['spec']['branch']!='FORECAST'}
    specs={r['request_id']:r for r in [*pilot['requests'],*packet['requests']]}
    if set(expected)!=set(specs) or len(expected)!=720:raise ValueError('incomplete original schedule')
    raw=[];seen=set();paths=[]
    for directory,is_prior in ((prior,True),(new,False)):
        identity=read(directory/'run.json')
        if identity['mode']!='hf' or identity['model']!=pilot['config']['model']:
            raise ValueError('only the actual pinned model may enter the real report')
        if identity['packet_sha256']!=(packet['pilot_packet_sha256'] if is_prior else sha):
            raise ValueError('collection identity mismatch')
        for path in sorted(directory.glob('*.response.json')):
            row=read(path);rid=row['request_id']
            if rid in seen or rid not in expected:raise ValueError('unknown or duplicate choice')
            if row['record_sha256']!=digest({k:v for k,v in row.items() if k!='record_sha256'}):raise ValueError('record changed')
            if any(row.get(k)!=v for k,v in identity.items()):raise ValueError('mixed run identity')
            if row['prompt_sha256']!=expected[rid]['prompt_sha256'] or row['seed']!=specs[rid]['seed']:raise ValueError('prompt or seed changed')
            if is_prior and (rid not in packet['prior_results'] or file_sha(path)!=packet['prior_results'][rid]['file_sha256']):
                raise ValueError('pilot output changed')
            if not is_prior and rid in packet['prior_results']:raise ValueError('pilot rerun forbidden')
            seen.add(rid);raw.append(row);paths.append(path)
    if not set(packet['prior_results']).issubset(seen):raise ValueError('missing original pilot response')
    # The older parser accepts surrounding whitespace. This run's stricter
    # collection status is authoritative. Preserve originals, mask only here.
    score_rows=[dict(r,raw_response=r['raw_response'] if r.get('status')=='VALID' and r.get('raw_response') in ('1','2','3') else '') for r in raw]
    score=descriptives(plan,bank,bundles,ledger,score_rows)
    # The parent ledger includes forecast queries, but none were requested here.
    del score['invalid_or_missing']
    by_raw={r['request_id']:r for r in raw};by_id={b['bundle_id']:b for b in bundles}
    evidence={b['bundle_id']:history_evidence(b) for b in bundles}
    details=[];regrets=defaultdict(lambda:defaultdict(list));branch_counts=defaultdict(Counter)
    for rid,row in expected.items():
        s=row['spec'];b=by_id[row['bundle_id']];response=by_raw.get(rid)
        raw_text=response.get('raw_response') if response else None
        valid=raw_text in ('1','2','3') and response['status']=='VALID'
        branch_counts[s['branch']]['planned']+=1;branch_counts[s['branch']]['valid']+=valid
        texts,vectors=grounded_candidates(bank,b,s)
        who=1-s['recipient'] if s['rebound'] else s['recipient']
        target_p=[.5]*3 if s['branch']=='RANDOM_RESPONSE' else [.38+.34*v[b['types'][who]] for v in vectors]
        c=int(raw_text)-1 if valid else None
        reg=None
        if valid and s['branch'] in ('BIND','TRANSFER','NEAR'):
            posterior=np.array(evidence[b['bundle_id']][who]['posterior_uniform_prior'])
            predicted=.38+.34*np.array(vectors).dot(posterior)
            reg=max(0.,float(predicted.max()-predicted[c]));regrets[s['branch']][b['bundle_id']].append(reg)
        details.append({'request_id':rid,'bundle_id':b['bundle_id'],'family':b['grounded_family'],
                        'source':'original_pilot' if rid in packet['prior_results'] else 'extension',
                        'status':'valid' if valid else 'missing' if response is None else 'invalid',
                        'raw_output':raw_text,'selected_message':texts[c] if valid else None,
                        'registered_vector':vectors[c] if valid else None,
                        'candidate_simulator_probabilities':target_p,'selected_expected_p_a':target_p[c] if valid else None,
                        'observed_new_target_choice':None,'posterior_expected_regret':reg})
    complete=sum(c['valid'] for c in branch_counts.values())==720
    regret_summary={}
    for branch,groups in regrets.items():
        if complete:
            values=[statistics.mean(groups[b['bundle_id']]) for b in bundles]
            regret_summary[branch]={'mean':statistics.mean(values),'sample_sd':statistics.stdev(values),'n_bundles':36}
    baselines={name:read(source/f'evaluation/{name}.analysis.json') for name in (*SHALLOW,*REFERENCES)}
    summary=dict(score,status='DESCRIPTIVE_FOLLOWUP_NOT_CONFIRMATION',valid_choices=sum(c['valid'] for c in branch_counts.values()),
                 planned_choices=720,unrequested_forecasts=144,branch_counts={k:dict(v) for k,v in branch_counts.items()},
                 actual_new_responses=len(raw)-60,original_pilot_responses=60,baselines=baselines,
                 model=pilot['config']['model'],revision=pilot['config']['revision'],
                 posterior_regret=regret_summary,requests=details,confidence_intervals=None,p_values=None,
                 packet_sha256=sha,complete=complete)
    output.mkdir(parents=True,exist_ok=False);write_new(output/'summary.json',summary)
    lines=['# Complete fixed bank collection report','',f"Model: {summary['model']}; revision `{summary['revision']}`.",
           f"Valid choices: {summary['valid_choices']}/720 from 36 bundles. Original 60 retained; {len(raw)-60} new records.",
           'This followup was selected after the pilot. No confirmatory tests or retrospective gate passes are reported.',
           'All missing or invalid choice cells remain in conservative score bounds. Forecasts were not requested.',
           '', '| Source | Binding | Transfer | Paraphrase | No history familiar | No history composite | Random |',
           '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for name,res in [(summary['model'],score),*baselines.items()]:
        lines.append('| '+name+' | '+' | '.join(f'{lo:.3f}' if abs(lo-hi)<1e-12 else f'[{lo:.3f}, {hi:.3f}]' for lo,hi in zip(res['mean_lower'],res['mean_upper']))+' |')
    lines += ['', 'These normalized contrasts are not success rates. The random control uses pseudo type geometry.',
              'The three annotated references receive privileged information. The additive task does not identify a unique latent mechanism.',
              '', '## Every bundle', '', '| Bundle | Binding | Transfer | Paraphrase | No history familiar | No history composite | Random |',
              '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for i,b in enumerate(bundles):
        lines.append('| '+b['bundle_id']+' | '+' | '.join(f'{lo:.3f}' if abs(lo-hi)<1e-12 else f'[{lo:.3f}, {hi:.3f}]' for lo,hi in zip(score['bundle_lower'][i],score['bundle_upper'][i]))+' |')
    lines += ['', '## Every raw model choice', '', 'Simulator expectations below are not newly sampled target outcomes.']
    for row in details:
        lines += ['', '### '+row['request_id'], '',f"Source: {row['source']}. Status: {row['status']}. Raw output: {row['raw_output']!r}.",
                  f"Selected message: {row['selected_message']}",f"Registered vector: {row['registered_vector']}",
                  f"P(A) for all three candidates: {row['candidate_simulator_probabilities']}"]
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')
    write_new(output/'manifest.json',{'inputs':{str(p):file_sha(p) for p in [*paths,source/'manifest.json',package/'extension_packet.json',Path(__file__)]},
                                      'outputs':{p.name:file_sha(p) for p in output.iterdir() if p.is_file()}})
    return {k:summary[k] for k in ('status','valid_choices','actual_new_responses','mean_lower','complete')}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','package','prior','new','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();print(json.dumps(analyze(args.source,args.package,args.prior,args.new,args.output)))
