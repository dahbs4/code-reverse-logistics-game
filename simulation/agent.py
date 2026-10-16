"""Rule-based controller using the same Action contract as the player."""
import argparse
import json
from pathlib import Path
from .engine import new_game,observe,apply_action,advance,terminal

def policy(observation):
    sites={}
    for site, info in observation['sites'].items():
        p=dict(info['plan']);q=info['inventory']
        p['carrier']='National Express' if q['upstream']>400000 else 'Value Freight'
        p['overtime']=2 if q['staging']>50000 else 0
        p['dispatch']=70 if site=='IND' else 38
        p['appointments']=6 if site=='IND' else 4
        if q['receiving']>q['staging']*2 and p['processing']>30:
            transfer=min(5,p['processing']-30);p['processing']-=transfer;p['warehouse']+=transfer
        if q['yard']>info['yard_capacity']*.75 and p['processing']>30:
            transfer=min(5,p['processing']-30);p['processing']-=transfer;p['receiving']+=transfer
        p['invest']=info['equipment']<1.3 and observation['hour']==0 and observation['scenario']['id']=='breakdown'
        sites[site]=p
    return {'sites':sites,'routing':{},'demand_override':1}

def run(scenario,seed,output):
    s=new_game(scenario,seed)
    with Path(output).open('w') as f:
        while not terminal(s)['done']:
            obs=observe(s);action=policy(obs);apply_action(s,action);advance(s,24);after=observe(s)
            f.write(json.dumps(dict(seed=seed,observation=obs,available_actions=obs['available_actions'],action=action,result=after,reward=after['reward'],terminal=after['terminal']))+'\n')
    return observe(s)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scenario',default='stable');p.add_argument('--seed',type=int,default=42);p.add_argument('--output',default='/tmp/reverse-network-episode.jsonl');args=p.parse_args()
    o=run(args.scenario,args.seed,args.output);print(json.dumps({'hour':o['hour'],'score':o['score'],'terminal':o['terminal']}))
