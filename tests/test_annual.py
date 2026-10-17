import copy
import json

import pytest

from simulation.engine import CONFIG, advance, apply_action, inventory, lot, new_game, observe, terminal, weekly_throughput
from simulation.forecast import annual_forecast


@pytest.mark.parametrize('site,month,overtime,expected', [
    ('EAST', 5, 0, 450000), ('EAST', 6, 0, 420000),
    ('EAST', 7, 0, 420000), ('EAST', 8, 0, 450000),
    ('EAST', 6, 4, 500000), ('IND', 6, 4, 1000000),
])
def test_physical_weekly_limits_enforced_despite_abundant_labor(site, month, overtime, expected):
    config = copy.deepcopy(CONFIG)
    config.update(weekly_units=0, event_probability=0)
    config['sites'][site]['queue_capacity'] = 2000000
    state = new_game(config=config)
    state['scenario']['start_date'] = f'2026-{month:02}-01'
    lot(state, 'TEST', site, 'DC Salvage', 1500000, 'staging')
    state['initial'] = 1500000
    plan = dict(state['plans'][site], receiving=0, warehouse=0,
                processing=state['config']['sites'][site]['max_workers'], overtime=overtime, hold=True)
    apply_action(state, {'sites': {site: plan}})
    advance(state, 168)
    assert state['site_processed'][site] == expected
    assert state['initial'] == state['disposed'] + sum(inventory(state).values())


def test_forecast_only_revises_at_week_close_and_survives_save_restore():
    state = new_game(seed=137)
    initial = annual_forecast(state)
    assert len(initial['weeks']) == 52
    advance(state, 24)
    partial = annual_forecast(state)
    assert partial['completed_weeks'] == 0
    assert partial['revision_factor'] == 1
    assert partial['projected_total'] == initial['projected_total']
    assert partial['weeks'][0]['actual_to_date'] == state['generated']
    assert partial['weeks'][0]['actual'] is None
    checkpoint = json.loads(json.dumps(state))
    advance(state, 144)
    revised = annual_forecast(state)
    assert revised['completed_weeks'] == 1
    assert revised['weeks'][0]['actual'] == state['generated']
    assert revised['actual_total'] == state['generated']
    assert revised['projected_total'] == revised['actual_total'] + revised['remaining_forecast']
    assert annual_forecast(checkpoint) == partial
    assert annual_forecast(json.loads(json.dumps(state))) == revised
    before = state['generated']
    state['demand_override'] = 2
    overridden = annual_forecast(state)
    assert overridden['weeks'][0]['outlook'] == revised['weeks'][0]['outlook']
    assert overridden['remaining_forecast'] > revised['remaining_forecast']
    assert state['generated'] == before


def test_full_52_week_campaign_and_no_early_backlog_termination():
    config = copy.deepcopy(CONFIG)
    config.update(weekly_units=0, event_probability=0)
    state = new_game(config=config)
    state['config']['loss_backlog_days'] = -1  # Trigger warning throughout.
    advance(state, 168)
    assert terminal(state)['backlog_warning']
    assert not terminal(state)['done']
    advance(state, 364 * 24)
    assert state['hour'] == 8736
    assert terminal(state)['done'] and terminal(state)['outcome'] == 'lost'
    forecast = annual_forecast(state)
    assert forecast['completed_weeks'] == 52
    assert forecast['remaining_forecast'] == 0


def test_summer_boundary_and_forecast_difficulty_pulses():
    state = new_game()
    state['scenario']['start_date'] = '2026-05-29'
    assert weekly_throughput(state, 'EAST', 0)['normal'] == 450000
    assert weekly_throughput(state, 'EAST', 72)['normal'] == 420000
    hard = new_game(difficulty='hard')
    assert hard['removal_baseline'][0] == round(state['removal_baseline'][0] * 1.1)
    assert new_game('peak')['removal_baseline'][1] > new_game('peak')['removal_baseline'][0]


def test_legacy_saves_do_not_invent_removal_actuals():
    state = new_game()
    del state['removal_baseline']
    del state['removal_actuals']
    assert observe(state)['annual_forecast'] is None


def test_revision_uses_only_last_four_completed_weeks():
    state = new_game()
    state['hour'] = 5 * 168
    state['removal_actuals'][:5] = [10 * state['removal_baseline'][0]] + [
        round(value * 1.2) for value in state['removal_baseline'][1:5]]
    forecast = annual_forecast(state)
    assert forecast['revision_factor'] == 1.2
    assert forecast['actual_total'] == sum(state['removal_actuals'][:5])
    assert forecast['weeks'][5]['forecast'] == round(state['removal_baseline'][5] * 1.2)
