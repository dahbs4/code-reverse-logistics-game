"""Weekly capacity planning: removals, processing, and carryover inventory."""
from datetime import datetime, timedelta
from math import ceil

from .forecast import annual_forecast, expected_removals
from .models import WeeklyPlan


def defaults(state):
    month = datetime.fromisoformat(state['scenario']['start_date']).month
    return {'IND': state['config']['sites']['IND'].get('typical_weekly_throughput', 600000), 'EAST': 420000 if month in (6, 7) else 450000}


def limits(state, first_hour, hours=168):
    result = {}
    for site in ('IND', 'EAST'):
        cfg = state['config']['sites'][site]
        normal = 0
        for hour in range(first_hour, first_hour + hours):
            month = (datetime.fromisoformat(state['scenario']['start_date']) + timedelta(hours=hour)).month
            if site == 'IND':
                normal += cfg.get('typical_weekly_throughput', 600000)
            elif month in (6, 7):
                normal += cfg.get('summer_weekly_throughput', 420000)
            else:
                normal += cfg.get('weekly_throughput', 450000)
        maximum = cfg.get('max_weekly_throughput', 1000000 if site == 'IND' else 500000)
        factor = state['scenario']['acceptance_factor']
        if site == 'IND':
            factor *= state['scenario']['equipment_factor']
        result[site] = {'normal': round(normal / 168), 'maximum': round(maximum * hours / 168),
                        'available': int(maximum * hours / 168 * factor)}
    return result


def validate_plan(state, plan):
    values = WeeklyPlan.model_validate(plan).model_dump()
    for site, units in values.items():
        maximum = state['config']['sites'][site].get('max_weekly_throughput', 1000000 if site == 'IND' else 500000)
        if units > maximum:
            raise ValueError(f'{site}: planned units exceed the {maximum:,} weekly maximum')
    return values


def outlook(state, plan=None):
    plan = validate_plan(state, plan or state.get('weekly_plan', defaults(state)))
    annual = annual_forecast(state)
    from .engine import inventory
    backlog = {site: sum(inventory(state, site).values()) for site in plan}
    shares = {site: list(state['routing'].values()).count(site) / len(state['routing']) for site in plan}
    rows = []
    first = state['hour'] // 168
    horizon = state['config']['horizon_days'] * 24
    revision = annual['revision_factor'] if annual else 1
    for index in range(first, ceil(horizon / 168)):
        start = max(state['hour'], index * 168)
        hours = min((index + 1) * 168, horizon) - start
        if hours <= 0:
            continue
        forecast = (annual['weeks'][index]['forecast'] if annual else round(sum(
            expected_removals(state['config'], state['scenario']['start_date'], h, state['difficulty'])
            for h in range(index * 168, min((index + 1) * 168, horizon))) * revision))
        # Older saves can be partway through a week. Forecast only its remainder.
        forecast = round(forecast * hours / min(168, horizon - index * 168))
        capacities = limits(state, start, hours)
        sites = {}
        allocated = 0
        for site in ('IND', 'EAST'):
            arrivals = round(forecast * shares[site]) if site == 'IND' else forecast - allocated
            allocated += arrivals
            planned = round(plan[site] * hours / 168)
            processed = min(backlog[site] + arrivals, planned, capacities[site]['available'])
            sites[site] = dict(starting_backlog=backlog[site], forecast=arrivals, planned=planned,
                               projected_processed=processed, ending_backlog=backlog[site] + arrivals - processed,
                               **capacities[site])
            backlog[site] = sites[site]['ending_backlog']
        rows.append(dict(week=index + 1, hours=hours, start=(datetime.fromisoformat(state['scenario']['start_date']) + timedelta(hours=start)).date().isoformat(),
                         forecast=forecast, planned=sum(x['planned'] for x in sites.values()),
                         projected_processed=sum(x['projected_processed'] for x in sites.values()),
                         starting_backlog=sum(x['starting_backlog'] for x in sites.values()),
                         ending_backlog=sum(backlog.values()), sites=sites))
    return dict(plan=plan, weeks=rows, next_week=rows[0] if rows else None,
                year_end_backlog=sum(backlog.values()),
                remaining_forecast=sum(row['forecast'] for row in rows),
                remaining_processing=sum(row['projected_processed'] for row in rows))


def commit(state, plan):
    from .engine import inventory, scorecard
    values = validate_plan(state, plan)
    state['weekly_plan'] = values
    state['decisions'].append(dict(hour=state['hour'], action={'weekly_units': values},
        before={site: inventory(state, site) for site in values}, after={site: inventory(state, site) for site in values},
        cost=sum(state['costs'].values()), score=scorecard(state)['overall']))


def advance_week(state):
    """Execute one aggregate operating week; no manual daily logistics controls."""
    from .engine import inventory, invariant, lot, rng_for, snapshot
    start = state['hour']
    hours = min(168 - start % 168, state['config']['horizon_days'] * 24 - start)
    if hours <= 0:
        return state
    config = state['config']
    plan = validate_plan(state, state.get('weekly_plan', defaults(state)))
    capacities = limits(state, start, hours)
    random = rng_for(state)
    starting_inventory = sum(inventory(state).values())
    # Seeded weekly variation; the forecast never sees this draw before execution.
    variation = random.uniform(.95, 1.05)
    shares = {site: list(state['routing'].values()).count(site) / len(state['routing']) for site in plan}
    expected = sum(expected_removals(config, state['scenario']['start_date'], h, state['difficulty']) for h in range(start, start + hours))
    generated = round(expected * variation)
    assigned = 0
    for site in plan:
        units = round(generated * shares[site]) if site == 'IND' else generated - assigned
        assigned += units
        category_assigned = 0
        categories = list(config['category_mix'].items())
        for i, (category, share) in enumerate(categories):
            quantity = round(units * share) if i < len(categories) - 1 else units - category_assigned
            category_assigned += quantity
            lot(state, 'WEEKLY', site, category, quantity, 'upstream', born=start)
    state['generated'] += generated
    if 'removal_actuals' in state:
        state['removal_actuals'][start // 168] += generated
    state['hour'] += hours
    processed_before = state['disposed']
    for site in plan:
        planned = round(plan[site] * hours / 168)
        remaining = min(planned, capacities[site]['available'])
        processed = 0
        effort_total = 0
        for freight in sorted(state['lots'], key=lambda x: x['born']):
            if freight['site'] != site or remaining <= 0:
                continue
            quantity = min(freight['units'], remaining)
            freight['units'] -= quantity
            remaining -= quantity
            processed += quantity
            effort_total += quantity * config['effort'][freight['category']]
            state['disposed'] += quantity
            if state['hour'] - freight['born'] <= config['score_targets']['service_hours']:
                state['totals']['on_time'] += quantity
            value = config['recovery'][freight['category']] * (config['high_value_share'] * config['high_value_multiplier'] + (1-config['high_value_share']) * config['low_value_multiplier'])
            state['revenue'] += quantity * value
            left = quantity
            for i, (kind, share) in enumerate(config['disposition_mix'].items()):
                count = left if i == len(config['disposition_mix']) - 1 else int(quantity * share)
                state['dispositions'][kind] += count
                left -= count
        state.setdefault('site_processed', {}).setdefault(site, 0)
        state['site_processed'][site] += processed
        state['totals']['processed'] += processed
        state['totals']['received'] += processed
        state['totals']['staged'] += processed
        state['totals']['processing_effort'] += effort_total
        weighted_effort = sum(config['effort'][cat] * share for cat, share in config['category_mix'].items())
        state['totals']['processing_capacity'] += min(planned, capacities[site]['available']) * weighted_effort
        loads = ceil(processed / config['trailer_units'])
        state['totals']['tendered'] += loads
        state['totals']['accepted'] += loads
        state['costs']['transport'] += loads * config['carriers']['Value Freight']['rate']
        # Automatically sized regular labor; surge above the usual rate has an overtime premium.
        labor = processed * config['labor_rate'] * weighted_effort / config['productivity']['processing']
        state['costs']['labor'] += labor
        state['costs']['overtime'] += (max(0, processed - capacities[site]['normal']) if site == 'EAST' else 0) * config['labor_rate'] * weighted_effort / config['productivity']['processing'] * (config['overtime_multiplier'] - 1)
    state['lots'] = [x for x in state['lots'] if x['units'] > 0]
    state['costs']['storage'] += (starting_inventory + sum(inventory(state).values())) / 2 * hours * config['storage_unit_hour']
    state['rng'] = random.getstate()
    state['last_week'] = dict(week=start // 168 + 1, removals=generated, processed=state['disposed'] - processed_before,
                              ending_backlog=sum(inventory(state).values()), planned=sum(plan.values()))
    # Weekly operation consolidates all unprocessed freight as carryover at origins.
    for freight in state['lots']:
        freight['state'] = 'upstream'
    invariant(state)
    snapshot(state, state['disposed'] - processed_before)
    return state
