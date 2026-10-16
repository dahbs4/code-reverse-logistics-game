"""Deterministic simulated players using only the public observation/action contract.

These heuristics demonstrate different operating styles; none is an optimal
controller or guaranteed to win. Policies never mutate their observations.
"""
from copy import deepcopy
from math import ceil

from .agent import policy as baseline_policy


def hands_off(observation):
    """Keep the current operating plan without making new investments."""
    return {"sites": {}, "routing": {}, "demand_override": 1}


def baseline(observation):
    """Wrap the original demonstration controller without sharing mutable data."""
    return baseline_policy(deepcopy(observation))


def _allocate(info, workers):
    """Allocate a roster by observed queue pressure and per-worker capacity."""
    queues = {"receiving": "yard", "warehouse": "receiving", "processing": "staging"}
    weights = {}
    for department, queue in queues.items():
        staff = info["plan"][department]
        # Removing overtime before using per-worker rates keeps repeated decisions
        # from mistaking an overtime boost for permanent productivity.
        rate = info["capacity"][department] / max(1, staff + (
            info["plan"]["temporary"] if department == "processing" else 0))
        rate /= 1 + info["plan"]["overtime"] / 8
        weights[department] = (1 + info["inventory"][queue] / 100000) / max(1, rate)
    total = sum(weights.values())
    limits = {"receiving": 250, "warehouse": 250, "processing": 350}
    allocation = {key: min(limits[key], int(workers * weight / total))
                  for key, weight in weights.items()}
    # Deterministic tie-breaking also distributes rounding leftovers.
    while sum(allocation.values()) < workers:
        eligible = [key for key in allocation if allocation[key] < limits[key]]
        if not eligible:
            break
        key = max(eligible, key=lambda key: weights[key] / (allocation[key] + 1))
        allocation[key] += 1
    return allocation


def cost_conscious(observation):
    """Favor value freight, regular labor, and modest queue-based staffing."""
    plans = {}
    for site, info in observation["sites"].items():
        plan = dict(info["plan"])
        inventory = info["inventory"]
        # Retain a regular roster ceiling instead of chasing every backlog spike.
        workers = min(info["max_workers"], 198 if site == "IND" else 109)
        plan.update(_allocate(info, workers))
        plan.update(overtime=0, temporary=0, carrier="Value Freight", expedite=False,
                    supplemental=0, invest=False, hold=False, priority="Oldest first")
        plan["dispatch"] = min(200, max(1, ceil(inventory["upstream"] /
                                                   observation["constraints"]["trailer_units"] / 10)))
        plan["appointments"] = 5 if site == "IND" else 3
        plans[site] = plan
    return {"sites": plans, "routing": {}, "demand_override": 1}


def adaptive_throughput(observation):
    """Use the roster and targeted overtime to relieve observed bottlenecks."""
    plans = {}
    for site, info in observation["sites"].items():
        plan = dict(info["plan"])
        inventory = info["inventory"]
        plan.update(_allocate(info, min(info["max_workers"], 850)))
        pressure = max(info["upstream_days"], info["yard_days"])
        active = [event for event in observation["events"]
                  if event["site"] == site and event["start"] <= observation["hour"] < event["end"]]
        disrupted = any(event["kind"] == "Carrier disruption" for event in active)
        plan.update(overtime=4 if pressure > 8 else 2 if pressure > 3 else 0,
                    temporary=0, carrier="National Express" if pressure > 5 or disrupted else "Value Freight",
                    expedite=pressure > 12, supplemental=0, invest=False,
                    hold=False, priority="Oldest first")
        plan["dispatch"] = min(200, max(1, ceil(inventory["upstream"] /
                                                   observation["constraints"]["trailer_units"] / 4)))
        plan["appointments"] = 20
        # Invest only once at the start of the known equipment-breakdown challenge.
        plan["invest"] = observation["hour"] == 0 and observation["scenario"]["id"] == "breakdown"
        plans[site] = plan
    return {"sites": plans, "routing": {}, "demand_override": 1}


PLAYERS = {
    "baseline": baseline,
    "hands_off": hands_off,
    "cost_conscious": cost_conscious,
    "adaptive_throughput": adaptive_throughput,
}

DESCRIPTIONS = {
    "baseline": "Original demonstration player: fixed dispatch targets and small queue-based labor transfers.",
    "hands_off": "Keeps the existing operating plan with no new decisions or investments.",
    "cost_conscious": "Uses value freight, regular labor, and queue-based allocation without overtime or investment.",
    "adaptive_throughput": "Uses the available roster, queue-based allocation, and pressure-triggered overtime and faster freight.",
}
