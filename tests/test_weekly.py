import copy
import json

import pytest

from simulation.engine import inventory, new_game, terminal
from simulation.models import StepRequest
from simulation.weekly import advance_week, commit, outlook


def test_weekly_outlook_is_pure_and_conserves_projected_units():
    state = new_game()
    before = copy.deepcopy(state)
    slow = outlook(state, {'IND': 500000, 'EAST': 200000})
    fast = outlook(state, {'IND': 1000000, 'EAST': 450000})
    assert state == before
    assert len(fast['weeks']) == 52
    assert fast['remaining_forecast'] == slow['remaining_forecast']
    assert fast['year_end_backlog'] < slow['year_end_backlog']
    for row in fast['weeks']:
        assert row['ending_backlog'] == row['starting_backlog'] + row['forecast'] - row['projected_processed']
        assert row['projected_processed'] <= row['planned']
        for site in row['sites'].values():
            assert site['projected_processed'] <= site['available']
            assert site['ending_backlog'] >= 0


def test_zero_plan_and_site_inventory_are_independent():
    state = new_game()
    result = outlook(state, {'IND': 1000000, 'EAST': 0})
    east = result['next_week']['sites']['EAST']
    assert east['projected_processed'] == 0
    assert east['ending_backlog'] == east['starting_backlog'] + east['forecast']
    commit(state, {'IND': 0, 'EAST': 0})
    before = sum(inventory(state).values())
    advance_week(state)
    assert state['disposed'] == 0
    assert sum(inventory(state).values()) == before + state['generated']


def test_weekly_execution_updates_actuals_and_survives_restore_deterministically():
    state = new_game(seed=137)
    commit(state, {'IND': 900000, 'EAST': 450000})
    restored = json.loads(json.dumps(state))
    advance_week(state)
    advance_week(restored)
    assert json.dumps(state, sort_keys=True) == json.dumps(restored, sort_keys=True)
    assert state['hour'] == 168
    assert state['last_week']['processed'] <= 1350000
    assert state['removal_actuals'][0] == state['generated']
    assert state['initial'] + state['generated'] == state['disposed'] + sum(inventory(state).values())


def test_entire_year_and_no_advancement_after_end():
    state = new_game()
    for i in range(52):
        advance_week(state)
        assert state['hour'] == (i + 1) * 168
        assert terminal(state)['done'] == (i == 51)
        assert state['last_week']['processed'] <= sum(state['weekly_plan'].values())
    assert sum(state['removal_actuals']) == state['generated']
    before = copy.deepcopy(state)
    advance_week(state)
    assert state == before


def test_seasonal_and_scenario_limits_and_invalid_targets():
    state = new_game()
    commit(state, {'IND': 1000000, 'EAST': 500000})
    result = outlook(state)
    assert any(row['sites']['EAST']['normal'] == 420000 for row in result['weeks'])
    assert result['next_week']['sites']['EAST']['maximum'] == 500000
    crisis = outlook(new_game('crisis'))
    assert crisis['next_week']['sites']['IND']['available'] == 500000
    breakdown = outlook(new_game('breakdown'))
    assert breakdown['next_week']['sites']['IND']['available'] == 550000
    for plan in ({'IND': 1000001, 'EAST': 0}, {'IND': 0, 'EAST': -1}, {'IND': 0, 'EAST': 500001}):
        with pytest.raises(ValueError):
            commit(state, plan)
    for hours in (8, 24):
        with pytest.raises(ValueError):
            StepRequest(hours=hours)


def test_partial_legacy_week_closes_at_next_boundary():
    state = new_game()
    state['hour'] = 24
    result = outlook(state)
    assert result['next_week']['hours'] == 144
    advance_week(state)
    assert state['hour'] == 168


@pytest.mark.parametrize('scenario', ['stable', 'crisis', 'breakdown'])
def test_preview_and_execution_apply_same_capacity_constraints(scenario):
    from simulation.engine import CONFIG, lot
    config = copy.deepcopy(CONFIG)
    config['weekly_units'] = 0
    state = new_game(scenario, config=config)
    for site in ('IND', 'EAST'):
        lot(state, 'TEST', site, 'Store Salvage', 2000000, 'upstream')
    state['initial'] = 4000000
    commit(state, {'IND': 1000000, 'EAST': 500000})
    expected = outlook(state)['next_week']
    advance_week(state)
    assert state['last_week']['processed'] == expected['projected_processed']
    assert state['last_week']['ending_backlog'] == expected['ending_backlog']
