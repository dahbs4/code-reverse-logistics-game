"""Campaign-wide removal forecasts revised only after complete operating weeks."""
from datetime import datetime, timedelta

WEEK_HOURS = 168


def expected_removals(config, start, hour, difficulty):
    day = datetime.fromisoformat(start) + timedelta(hours=hour)
    seasonal = (config['holiday_multiplier'] if
                (day.month == 12 and day.day >= config['holiday_start']) or
                (day.month == 1 and day.day <= 7) else
                config['seasonality'].get(str(day.month), 1))
    mix = sum(share * (config['monthly_removal_multiplier'] if
              category == 'DC Salvage' and day.day == config['monthly_removal_day'] else 1)
              for category, share in config['category_mix'].items())
    return config['weekly_units'] / WEEK_HOURS * seasonal * mix * (1.1 if difficulty == 'hard' else 1)


def initialize_forecast(config, start, difficulty):
    hours = config['horizon_days'] * 24
    return [round(sum(expected_removals(config, start, h, difficulty)
                      for h in range(first, min(first + WEEK_HOURS, hours))))
            for first in range(0, hours, WEEK_HOURS)]


def annual_forecast(state):
    if 'removal_baseline' not in state:
        return None  # Older saves have no reliable weekly actuals ledger.
    baseline = state['removal_baseline']
    actuals = state['removal_actuals']
    completed = min(len(baseline), state['hour'] // WEEK_HOURS)
    recent = range(max(0, completed - 4), completed)
    expected = sum(baseline[i] for i in recent)
    factor = min(2, max(.5, sum(actuals[i] for i in recent) / expected)) if expected else 1
    weeks = []
    for i, original in enumerate(baseline):
        start = datetime.fromisoformat(state['scenario']['start_date']) + timedelta(weeks=i)
        done = i < completed
        forecast = round(original * factor * state['demand_override'])
        weeks.append(dict(week=i + 1, start=start.date().isoformat(), end=(start + timedelta(days=6)).date().isoformat(),
                          baseline=original, forecast=forecast, actual=actuals[i] if done else None,
                          actual_to_date=actuals[i], outlook=actuals[i] if done else forecast,
                          status='actual' if done else 'in progress' if i == completed and state['hour'] % WEEK_HOURS else 'forecast'))
    return dict(weeks=weeks, completed_weeks=completed, revision_factor=round(factor, 4),
                baseline_total=sum(baseline), actual_total=sum(actuals[:completed]),
                remaining_forecast=sum(w['forecast'] for w in weeks[completed:]),
                projected_total=sum(w['outlook'] for w in weeks), updated_hour=completed * WEEK_HOURS)
