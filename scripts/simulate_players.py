"""Run reproducible simulated player tournaments against the game engine.

Run from any directory with the repository virtualenv's Python interpreter.
"""
import argparse
from contextlib import nullcontext
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simulation.engine import SCENARIOS, advance, apply_action, invariant, new_game, observe, terminal
from simulation.players import DESCRIPTIONS, PLAYERS


def run_episode(player, scenario, seed, difficulty, trace_dir=None):
    """Run one player to a terminal state, checking conservation every turn."""
    state = new_game(scenario, seed, difficulty)
    trace_path = None
    if trace_dir is not None:
        trace_dir = Path(trace_dir)
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_path = trace_dir / f'{player}-{scenario}-{difficulty}-{seed}.jsonl'
    trace_context = trace_path.open('w') if trace_path else nullcontext(None)
    turns = 0
    with trace_context as trace:
        while not terminal(state)['done']:
            observation = observe(state)
            action = PLAYERS[player](observation)
            apply_action(state, action)
            advance(state, 24)
            invariant(state)
            turns += 1
            if trace:
                after = observe(state)
                trace.write(json.dumps(dict(player=player, scenario=scenario, seed=seed,
                    difficulty=difficulty, turn=turns, action=action, hour=after['hour'],
                    inventory=after['inventory'], disposed=after['disposed'],
                    generated=after['generated'], costs=after['costs'], score=after['score'],
                    reward=after['reward'], terminal=after['terminal'])) + '\n')
    result = observe(state)
    remaining = sum(result['inventory'].values())
    balance = result['initial'] + result['generated'] - result['disposed'] - remaining
    assert balance == 0, 'Freight conservation violated'
    assert result['terminal']['done'], 'Episode did not finish'
    return dict(player=player, scenario=scenario, seed=seed, difficulty=difficulty,
        hour=result['hour'], turns=turns, outcome=result['terminal']['outcome'],
        score=result['score'], initial=result['initial'], generated=result['generated'],
        processed=result['disposed'], inventory=result['inventory'], remaining=remaining,
        costs=result['costs'], total_cost=round(sum(result['costs'].values()), 2),
        revenue=round(result['revenue'], 2), conservation_balance=balance)


def report(results):
    lines = ['# Simulated player tournament', '',
        'Deterministic rule-based players use the same actions and engine as human players. '
        'Each turn advances up to 24 hours; engine invariants run every simulated hour. '
        'These seeded episodes compare strategies; they do not establish optimal play.', '',
        f'Episodes: {len(results)}. All terminal states reached; freight conservation balance is zero in every episode.', '',
        '| Player | Scenario | Difficulty | Runs | Wins | Mean score | Score range | Mean hours | Mean processed | Mean cost |',
        '| --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |']
    groups = {}
    for result in results:
        key = (result['player'], result['scenario'], result['difficulty'])
        groups.setdefault(key, []).append(result)
    for (player, scenario, difficulty), episodes in groups.items():
        scores = [e['score']['overall'] for e in episodes]
        mean = lambda field: statistics.mean(e[field] for e in episodes)
        wins = sum(e['outcome'] == 'won' for e in episodes)
        lines.append(f'| {player} | {scenario} | {difficulty} | {len(episodes)} | {wins} | '
                     f'{statistics.mean(scores):.1f} | {min(scores):.1f}–{max(scores):.1f} | '
                     f'{mean("hour"):.0f} | {mean("processed"):,.0f} | {mean("total_cost"):,.2f} |')
    lines.extend(['', '## Players', ''])
    for player in dict.fromkeys(r['player'] for r in results):
        lines.append(f'- **{player}**: {DESCRIPTIONS[player]}')
    lines.extend(['', 'Results include full score components, costs, remaining freight, and seeds in the accompanying JSON. '
                  'Wins use the engine’s target score and terminal rules. A backlog loss takes precedence over the score: '
                  'a peak-season episode can lose even with a score at or above 60. '
                  'Early losses may have fewer hours, processed units, and costs.', ''])
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--players', nargs='+', choices=list(PLAYERS), default=list(PLAYERS))
    parser.add_argument('--scenarios', nargs='+', choices=[s['id'] for s in SCENARIOS], default=[s['id'] for s in SCENARIOS])
    parser.add_argument('--seeds', nargs='+', type=int, default=[42, 137])
    parser.add_argument('--difficulties', nargs='+', choices=['standard', 'hard'], default=['standard'])
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/player-simulation-results.json')
    parser.add_argument('--report', type=Path, default=ROOT / 'docs/player-simulation-report.md')
    parser.add_argument('--trace-dir', type=Path, help='Optional directory for compact per-turn JSONL traces')
    args = parser.parse_args(argv)
    if any(seed < 0 or seed > 2147483647 for seed in args.seeds):
        parser.error('Seeds must be between 0 and 2147483647')
    started = time.monotonic()
    results = []
    for player in args.players:
        for scenario in args.scenarios:
            for difficulty in args.difficulties:
                for seed in args.seeds:
                    result = run_episode(player, scenario, seed, difficulty, args.trace_dir)
                    results.append(result)
                    print(f'{player:20} {scenario:10} {difficulty:8} seed={seed} '
                          f'score={result["score"]["overall"]:5.1f} {result["outcome"]}', flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + '\n')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report(results))
    print(f'{len(results)} episodes in {time.monotonic() - started:.1f}s; '
          f'results: {args.output}; report: {args.report}')
    return results


if __name__ == '__main__':
    main()
