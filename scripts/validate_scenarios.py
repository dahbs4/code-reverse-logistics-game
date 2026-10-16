"""Run complete seeded episodes, executing invariants at every simulated hour."""
import json
from pathlib import Path
from simulation.agent import run

results=[]
for scenario in ('stable','crisis','peak','breakdown'):
    for seed in (42,137):
        o=run(scenario,seed,f'/tmp/reverse-{scenario}-{seed}.jsonl')
        assert o['terminal']['done']
        assert o['initial']+o['generated']==o['disposed']+sum(o['inventory'].values())
        results.append(dict(scenario=scenario,seed=seed,hour=o['hour'],processed=o['disposed'],generated=o['generated'],inventory=sum(o['inventory'].values()),cost=sum(o['costs'].values()),score=o['score']['overall'],outcome=o['terminal']['outcome']))
        print(json.dumps(results[-1]),flush=True)
Path('docs/validation-results.json').write_text(json.dumps(results,indent=2)+'\n')
