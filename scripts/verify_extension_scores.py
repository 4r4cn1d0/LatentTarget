"""Check the vectorized report using an independent scalar contrast calculation."""
import argparse
from collections import defaultdict
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.build_diagnostic_packet import rows
from src.diagnostic_pilot import read,file_sha,write_new
from src.grounded_partner import grounded_candidates


def verify(source,summary_path):
    summary=read(summary_path)
    bundles=rows(source/'evaluation/bundles.jsonl.gz');bank=read(source/'bank_snapshot.json')
    by_id={b['bundle_id']:b for b in bundles}
    expected={r['request_id']:r for r in rows(source/'evaluation/ledger.jsonl.gz') if r['spec']['branch']!='FORECAST'}
    bounds=defaultdict(lambda:[0.,0.])
    if len(summary['requests'])!=720 or {r['request_id'] for r in summary['requests']}!=set(expected):
        raise ValueError('report omitted or duplicated requests')
    for actual in summary['requests']:
        row=expected[actual['request_id']];spec=row['spec'];b=by_id[row['bundle_id']]
        _,vectors=grounded_candidates(bank,b,spec)
        first,second=b['types'];delta=[v[first]-v[second] for v in vectors];span=max(delta)-min(delta)
        nohist=spec['branch']=='NO_HISTORY'
        sign=(1,-1)[spec['recipient']] if nohist else (1,-1,-1,1)[spec['cell']]
        coefficients=[sign*d/(span*(1 if nohist else 2)) for d in delta]
        if actual['status']=='valid':
            lo=hi=coefficients[int(actual['raw_output'])-1]
        else:lo,hi=min(coefficients),max(coefficients)
        metric='NO_HISTORY_'+spec['bank'] if nohist else spec['branch']
        bounds[(b['bundle_id'],metric)][0]+=lo;bounds[(b['bundle_id'],metric)][1]+=hi
    largest=0.
    for j,metric in enumerate(summary['metric_order']):
        for side,label in enumerate(('lower','upper')):
            values=[bounds[b['bundle_id'],metric][side] for b in bundles]
            largest=max(largest,abs(sum(values)/36-summary['mean_'+label][j]))
            largest=max(largest,max(abs(value-summary['bundle_'+label][i][j]) for i,value in enumerate(values)))
    if largest>1e-12:raise ValueError('independent scalar score disagrees')
    return {'status':'INDEPENDENT_SCORE_CHECK_PASSED','n_bundles':36,'planned_choices':720,
            'maximum_difference':largest,'summary_sha256':file_sha(summary_path),'script_sha256':file_sha(Path(__file__))}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--summary',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=verify(a.source,a.summary);write_new(a.output,result);print(result)
