"""Reproduce end-to-end results with standard-library Python."""
from collections import Counter, defaultdict
import json
from pathlib import Path
from random import Random

DATA=Path(__file__).resolve().parent/'data'


def outcome(item,polarity):
    if not item['valid']:
        return 'technical', (0,0)
    if polarity=='unsupported' and not item['edited']:
        return 'failure', (0,0)
    required=['wording_supported','substantive_relation_present','focal_factor_preserved']
    if polarity=='supported':
        required.append('target_assertion_preserved')
    fields=[item['fields'][k] for k in required]
    if False in fields:
        return 'failure',(0,0)
    if all(v is True for v in fields):
        return 'confirmed',(1,1)
    return 'unresolved',(0,1)


def interval(groups):
    def mean(values):
        return tuple(sum(v[j] for v in values)/len(values) for j in (0,1))
    incidents=[mean(values) for _,values in sorted(groups.items())]
    rng=Random(741102)
    samples=[mean(rng.choices(incidents,k=len(incidents))) for _ in range(20000)]
    return {'bounds':mean(incidents),'envelope95':(
        sorted(v[0] for v in samples)[499],sorted(v[1] for v in samples)[19499])}


def analyze(rows):
    counts=defaultdict(Counter)
    groups={key:defaultdict(list) for key in ('generic_gap','relation_minus_generic','postedit_minus_generic')}
    for row in rows:
        p=row['polarity']
        states={arm:outcome(item,p) for arm,item in row['arms'].items()}
        for arm,(label,bounds) in states.items():
            counts[arm,p][label]+=1
            counts[arm,p]['effective_edits']+=row['arms'][arm]['edited']
            counts[arm,p]['retain']+=row['arms'][arm]['decision']=='retain'
        if p!='unsupported':
            continue
        incident=row['incident']
        g=states['generic'][1]
        edited=int(row['arms']['generic']['edited'])
        groups['generic_gap'][incident].append((edited-g[1],edited-g[0]))
        for arm,name in [('relation_flat','relation_minus_generic'),('postedit','postedit_minus_generic')]:
            v=states[arm][1]
            if arm=='postedit' and row['same_verifier_wording'] and states[arm][0]==states['generic'][0]:
                delta=(0,0)
            else:
                delta=(v[0]-g[1],v[1]-g[0])
            groups[name][incident].append(delta)
    return {'counts':{f'{arm}/{p}':dict(v) for (arm,p),v in counts.items()},
            'estimates':{k:interval(v) for k,v in groups.items()}}


if __name__=='__main__':
    rows=json.loads((DATA/'attempts.json').read_text(encoding='utf-8'))
    assert len(rows)==100 and len({r['incident'] for r in rows})==25
    print(json.dumps(analyze(rows),indent=2))
