"""Player policies must remain valid as the network evolves."""
import copy

import pytest

from simulation.engine import advance, apply_action, invariant, new_game, observe
from simulation.players import PLAYERS


@pytest.mark.parametrize('player', list(PLAYERS))
@pytest.mark.parametrize('scenario', ['stable', 'crisis', 'peak', 'breakdown'])
def test_players_are_deterministic_valid_and_preserve_observations(player, scenario):
    state = new_game(scenario, seed=137)
    for _ in range(3):
        observation = observe(state)
        original = copy.deepcopy(observation)
        action = PLAYERS[player](observation)
        assert observation == original
        assert action == PLAYERS[player](copy.deepcopy(observation))
        apply_action(state, action)
        advance(state, 24)
        invariant(state)
    assert state['hour'] == 72
