"""Portable implementation of the evidence handoff and response contract.

A caller supplies the model callback. It receives the complete Ollama request
and returns one parsed response object. This module never initiates inference.
"""
from copy import deepcopy
import json
from pathlib import Path

PROMPTS=json.loads((Path(__file__).resolve().parent/'data/prompts.json').read_text(encoding='utf-8'))
ARMS=('iterative','generic','relation_flat','untyped_flat')
GROUPS=('link','qualification','alternative')
TEXT={'type':'string'}
NONEMPTY={'type':'string','minLength':1}
DECISIONS=('retain','revise','uncertain')


def obj(**properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}


def ids(units, minimum, maximum):
    return {'type':'array','items':{'type':'string','enum':sorted(units)},
            'minItems':minimum,'maxItems':maximum,'uniqueItems':True}


def validate(response,schema):
    if type(response) is not dict or set(response)!=set(schema['required']):
        raise ValueError('Response fields do not match the contract.')
    for name, rule in schema['properties'].items():
        v=response[name]
        if rule['type']=='string':
            if type(v) is not str or len(v)<rule.get('minLength',0) or ('enum' in rule and v not in rule['enum']):
                raise ValueError(f'Invalid string field {name}')
        elif type(v) is not list or not rule['minItems']<=len(v)<=rule['maxItems'] or any(
                type(k) is not str or k not in rule['items']['enum'] for k in v) or len(v)!=len(set(v)):
            raise ValueError(f'Invalid identifier list {name}')
    return response


def request(stage, packet, schema, seed):
    recipe=PROMPTS[stage]
    payload=deepcopy(recipe['options'])
    payload['options']['seed']=seed
    payload['format']=schema
    payload['messages']=[{'role':'system','content':recipe['system']},
                         {'role':'user','content':json.dumps(packet,ensure_ascii=False)}]
    return payload


def call_model(model,stage,packet,schema,seed):
    return validate(model(request(stage,packet,schema,seed)),schema)


def excerpts(units, selected):
    return [{'id':k,'text':units[k]} for k in selected]


def handoff(model,sources,seed):
    if len(sources)!=2 or any(not source['units'] for source in sources):
        raise ValueError('Provide two nonempty canonical source documents.')
    cards=[]
    for source in sources:
        unit=source['units']
        schema=obj(selected_units=ids(unit,1,min(2,len(unit))))
        returned=call_model(model,'source_card',source,schema,seed)
        cards.append({'id':source['id'],'excerpts':excerpts(unit,returned['selected_units'])})
    return cards


def workflow(model,sources,cards,original,arm,seed,verify=False):
    if arm not in ARMS or (verify and arm!='generic'):
        raise ValueError('The follow-up verifier applies to the generic workflow.')
    units={}
    for source in sources:
        if units.keys() & source['units'].keys():
            raise ValueError('Canonical paragraph IDs must be unique per incident.')
        units.update(source['units'])
    context=[ex['text'] for c in cards for ex in c['excerpts']]
    packet={'evidence':sources,'cards':cards,'draft':{'context_facts':context,'claim':original}}
    first={'relation_flat':obj(**{k:ids(units,0,3) for k in GROUPS}),
           'untyped_flat':obj(selected_units=ids(units,0,min(len(units),9)))}
    stage=call_model(model,arm,packet,first.get(arm,obj(memo=NONEMPTY)),seed)
    if arm=='relation_flat':
        stage={'excerpts':excerpts(units,sorted({i for k in GROUPS for i in stage[k]}))}
    elif arm=='untyped_flat':
        stage={'excerpts':excerpts(units,sorted(stage['selected_units']))}
    schema=obj(decision={'type':'string','enum':list(DECISIONS)}, reason=NONEMPTY,
               anchors=ids(units,1,3),wording=TEXT)
    draft=apply(original,call_model(model,'coordinator',dict(packet,review=stage),schema,seed))
    if verify:
        reviewed=call_model(model,'postedit',dict(packet,candidate_wording=draft['wording']),schema,seed)
        return apply(original,reviewed)
    return draft


def apply(original,response):
    decision=response['decision']
    wording=response['wording'] if decision=='revise' else original
    if decision=='revise' and not wording.strip():
        raise ValueError('A revision requires nonempty final wording.')
    return {'decision':decision,'wording':wording,'effective_change':wording!=original}
