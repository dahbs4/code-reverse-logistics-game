"""Deterministic weekly player strategies using the same two targets as humans."""


def hands_off(observation):
    return dict(observation['weekly_plan'])


def baseline(observation):
    return {'IND': 750000, 'EAST': 375000}


def cost_conscious(observation):
    return {'IND': 650000, 'EAST': 350000}


def adaptive_throughput(observation):
    week = observation['weekly_outlook']['next_week']
    if not week:
        return dict(observation['weekly_plan'])
    return {site: min(values['maximum'], max(0, round(values['forecast'] + values['starting_backlog'] / 4)))
            for site, values in week['sites'].items()}


PLAYERS = {'baseline': baseline, 'hands_off': hands_off,
           'cost_conscious': cost_conscious, 'adaptive_throughput': adaptive_throughput}
DESCRIPTIONS = {
    'baseline': 'Plans 750,000 Indianapolis units and 375,000 East Coast units each week.',
    'hands_off': 'Retains the initial weekly targets (600,000 Indianapolis and the seasonal East Coast default).',
    'cost_conscious': 'Plans 650,000 Indianapolis units and 350,000 East Coast units each week.',
    'adaptive_throughput': 'Plans forecast removals plus one quarter of site backlog, up to each site maximum.',
}
