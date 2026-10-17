"""Weekly rule-based controller using the same planning contract as the player."""
import argparse
import json
from pathlib import Path
from .engine import new_game, observe, terminal
from .weekly import commit, advance_week


def policy(observation):
    from .players import baseline
    return baseline(observation)


def run(scenario, seed, output):
    state = new_game(scenario, seed)
    with Path(output).open('w') as stream:
        while not terminal(state)['done']:
            before = observe(state)
            action = policy(before)
            commit(state, action)
            advance_week(state)
            after = observe(state)
            stream.write(json.dumps(dict(seed=seed, week=state['hour']//168,
                action=action, forecast=before['weekly_outlook']['next_week'],
                actuals=state['last_week'], reward=after['reward'], terminal=after['terminal']))+'\n')
    return observe(state)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--scenario',default='stable')
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--output',default='/tmp/reverse-network-episode.jsonl')
    args=parser.parse_args()
    result=run(args.scenario,args.seed,args.output)
    print(json.dumps({'hour':result['hour'],'score':result['score'],'terminal':result['terminal']}))
