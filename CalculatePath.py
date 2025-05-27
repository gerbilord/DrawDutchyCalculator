import json
import copy
from collections import defaultdict

# Define combat rules
COMBAT_RULES = {
    "archers": {"kills": "warriors", "ratio": (2, 3)},  # 2 archers kill 3 warriors
    "warriors": {"kills": "soldiers", "ratio": (2, 2)},  # 2 warriors kill 2 soldiers
    "soldiers": {"kills": "archers", "ratio": (2, 2)},  # 2 soldiers kill 2 archers
}

# Invert the combat rules for easier lookup of who kills whom
# This is for when unit A is attacked by unit B.
INVERSE_COMBAT_RULES = {}
for attacker, rules in COMBAT_RULES.items():
    killed_type = rules["kills"]
    INVERSE_COMBAT_RULES[killed_type] = {
        "killed_by": attacker,
        "ratio": rules["ratio"]
    }


def calculate_battle_outcome(unit1_type, unit1_amount, unit2_type, unit2_amount):
    """
    Calculates the outcome of a battle between two unit types.
    Returns (remaining_unit1_amount, remaining_unit2_amount)
    """
    if unit1_type == unit2_type or unit1_type == "typeless" or unit2_type == "typeless":
        # Trade evenly
        return (unit1_amount - unit2_amount, unit2_amount - unit1_amount)

    # Check if unit1 kills unit2
    if unit1_type in COMBAT_RULES and COMBAT_RULES[unit1_type]["kills"] == unit2_type:
        attacker_ratio, defender_ratio = COMBAT_RULES[unit1_type]["ratio"]
        # Calculate how many of unit2 are killed by unit1
        unit2_killed = (unit1_amount / attacker_ratio) * defender_ratio
        remaining_unit2 = unit2_amount - unit2_killed
        remaining_unit1 = unit1_amount  # Attacker doesn't lose units in this scenario
        return (remaining_unit1, remaining_unit2)

    # Check if unit2 kills unit1
    elif unit2_type in COMBAT_RULES and COMBAT_RULES[unit2_type]["kills"] == unit1_type:
        attacker_ratio, defender_ratio = COMBAT_RULES[unit2_type]["ratio"]
        # Calculate how many of unit1 are killed by unit2
        unit1_killed = (unit2_amount / attacker_ratio) * defender_ratio
        remaining_unit1 = unit1_amount - unit1_killed
        remaining_unit2 = unit2_amount  # Attacker doesn't lose units in this scenario
        return (remaining_unit1, remaining_unit2)

    # This case should ideally not be hit if combat rules are exhaustive
    # But for safety, if no specific rule, they trade evenly (or no effect, if you prefer)
    return (unit1_amount - unit2_amount, unit2_amount - unit1_amount)


def combine_units(unit1, unit2):
    """
    Combines two friendly units into one.
    Returns a new unit dictionary.
    """
    if unit1['team'] != unit2['team']:
        raise ValueError("Cannot combine units from different teams.")

    if unit1['amount'] >= unit2['amount']:
        new_type = unit1['type']
    else:
        new_type = unit2['type']

    new_amount = unit1['amount'] + unit2['amount']
    return {'type': new_type, 'amount': new_amount, 'team': unit1['team']}


def calculate_blue_advantage(units):
    """
    Calculates the total blue units minus total red units.
    """
    blue_units = sum(unit['amount'] for unit in units if unit['team'] == 'blue')
    red_units = sum(unit['amount'] for unit in units if unit['team'] == 'red')
    return blue_units - red_units


memo = {}


def find_best_path(current_units, remaining_indices, path_so_far):
    """
    Recursively finds the best path to maximize blue's advantage.

    Args:
        current_units (list): The current state of units (list of dicts).
        remaining_indices (tuple): A tuple of indices of units not yet used in the path.
        path_so_far (list): The sequence of operations performed to reach current_units.

    Returns:
        tuple: (max_advantage, best_path_operations)
    """
    state_key = (tuple(sorted([(u['type'], u['amount'], u['team']) for u in current_units])), remaining_indices)

    if state_key in memo:
        return memo[state_key]

    if not remaining_indices:
        advantage = calculate_blue_advantage(current_units)
        memo[state_key] = (advantage, path_so_far)
        return advantage, path_so_far

    max_advantage = -float('inf')
    best_path_operations = []

    # Iterate through all possible pairs for combination or battle
    for i_idx_in_remaining in range(len(remaining_indices)):
        idx1 = remaining_indices[i_idx_in_remaining]
        unit1 = current_units[idx1]

        # Try to combine with other friendly units
        for j_idx_in_remaining in range(i_idx_in_remaining + 1, len(remaining_indices)):
            idx2 = remaining_indices[j_idx_in_remaining]
            unit2 = current_units[idx2]

            if unit1['team'] == unit2['team']:
                # Combination
                new_unit = combine_units(unit1, unit2)

                # Create new unit list without the two combined units, and add the new combined unit
                next_units = [u for k, u in enumerate(current_units) if k != idx1 and k != idx2]
                next_units.append(new_unit)

                # Update remaining_indices to reflect removal of idx1 and idx2, and addition of a "new" unit
                # The index of the new unit will be len(next_units) - 1
                new_remaining_indices_list = [r for r in remaining_indices if r != idx1 and r != idx2]
                new_remaining_indices = tuple(
                    new_remaining_indices_list)  # No new index is added, as the previous indices for the combined units are removed.

                # Determine the actual index of the new unit in next_units for the recursive call
                # This logic assumes next_units is a list where new_unit is the last element
                # If we were to use indices directly for the recursive call, we'd need to map them.
                # For simplicity, we pass the new list and remaining_indices tuple, and the recursive call re-indexes if needed.

                # For the purpose of 'remaining_indices', we are tracking which *initial* units are still available.
                # When units combine, those initial units are consumed. The new combined unit effectively replaces them
                # in the available pool, but it doesn't have an original index in the same way.
                # The 'remaining_indices' should represent the indices of the *original* units that have not yet been touched.

                # Correct approach for remaining_indices after combination:
                # The units at idx1 and idx2 are "used up". The combined unit is a *new* entity
                # that doesn't have an original index. So, we simply remove idx1 and idx2 from
                # remaining_indices.

                op = f"Combine {unit1['amount']} {unit1['type']} ({unit1['team']}) with {unit2['amount']} {unit2['type']} ({unit2['team']}) -> {new_unit['amount']} {new_unit['type']} ({new_unit['team']})"

                # To handle the indexing correctly for the next recursive step,
                # we need to consider 'current_units' as a pool from which we draw.
                # When we combine, we create a 'new' unit. We need to effectively add this 'new' unit
                # to our 'current_units' list and remove the old ones, then update the indices.

                # A more robust way to manage `current_units` across recursive calls is to
                # always pass a *new* list of units reflecting the current state, and
                # `remaining_indices` should point to indices within that *new* list.
                # This means `remaining_indices` would need to be re-calculated for each call.

                # Let's modify `find_best_path` to work with a list of unit dictionaries directly,
                # and `remaining_indices` refers to indices within that list.

                # To correctly pass state to the next recursion:
                # 1. Create a deep copy of current_units to modify.
                temp_next_units = copy.deepcopy(list(current_units))  # Convert tuple to list for modification

                # Find original units in the deep copy to remove them
                # This is tricky because units in current_units might not be in the same order as initial_units.
                # A better approach: `remaining_indices` should be indices into the *initial* units list.
                # And `current_units` should represent the *current* state of the battlefield.
                # The problem statement says "Each unit can only go to one other unit. Such that you have a path that hits each group once."
                # This implies using the original unit groups as distinct entities.

                # Let's rethink the state for the recursion.
                # State should be `(current_battle_units, units_not_yet_involved_in_path_indices)`
                # `current_battle_units` would be a list of units that have either combined
                # or are waiting to battle.
                # `units_not_yet_involved_in_path_indices` would be indices from the *original* input.

                # This is a classic Traveling Salesperson Problem (TSP) style formulation.
                # Each "group" (initial unit) must be "visited" once.

                # Let's adjust the `find_best_path` signature and logic:
                # `find_best_path(current_state_units, unvisited_original_indices)`
                # `current_state_units`: The actual units present at this step (can be combined units).
                # `unvisited_original_indices`: Indices from the *initial* units list that haven't been part of any operation.

                # Reverting to the simpler interpretation of `remaining_indices`:
                # `remaining_indices` is the set of indices from the *initial* units list that are still 'available' to be chosen as `unit1` or `unit2`.

                # For combination: unit1 and unit2 are consumed. A new unit is created.
                # This new unit is not "from" the original list, so it doesn't have an `original_index`.
                # We need to treat it as a new entity in the `current_units` list for the next recursion.

                # The `remaining_indices` should only contain indices of units from the *original* input
                # that haven't been touched yet.

                # Let's redefine `current_units` as the `original_units` for clarity within this function.
                # We will create `next_state_units` for the recursive call.

                # Create the new list of units for the next state
                next_state_units_for_recursion = []
                new_indices_for_next_state = []

                # Add units that are not unit1 or unit2 from the current (original) units
                for k, u in enumerate(current_units):
                    if k != idx1 and k != idx2:
                        next_state_units_for_recursion.append(u)
                        if k in remaining_indices:  # Only add its index if it was originally remaining
                            new_indices_for_next_state.append(k)

                # Add the newly combined unit
                next_state_units_for_recursion.append(new_unit)

                # The key to this problem is correctly identifying when a "group" has been "hit".
                # If idx1 and idx2 are 'hit', they are removed from `remaining_indices`.
                # The combined unit is a *new* group.

                next_remaining_indices = tuple(sorted(list(set(remaining_indices) - {idx1, idx2})))

                # Recursive call
                advantage, path = find_best_path(tuple(next_state_units_for_recursion), next_remaining_indices,
                                                 path_so_far + [op])

                if advantage > max_advantage:
                    max_advantage = advantage
                    best_path_operations = path

        # Try to battle with other enemy units
        for j_idx_in_remaining in range(len(remaining_indices)):
            if i_idx_in_remaining == j_idx_in_remaining:
                continue  # Don't battle with self

            idx2 = remaining_indices[j_idx_in_remaining]
            unit2 = current_units[idx2]

            if unit1['team'] != unit2['team']:
                # Battle
                rem1, rem2 = calculate_battle_outcome(unit1['type'], unit1['amount'], unit2['type'], unit2['amount'])

                op = f"Battle {unit1['amount']} {unit1['type']} ({unit1['team']}) vs {unit2['amount']} {unit2['type']} ({unit2['team']}) -> "

                next_state_units_for_recursion = []
                new_indices_for_next_state = []

                if rem1 > 0:
                    next_state_units_for_recursion.append(
                        {'type': unit1['type'], 'amount': rem1, 'team': unit1['team']})
                    op += f"({rem1} {unit1['type']} {unit1['team']} left) "
                else:
                    op += f"({unit1['team']} {unit1['type']} eliminated) "

                if rem2 > 0:
                    next_state_units_for_recursion.append(
                        {'type': unit2['type'], 'amount': rem2, 'team': unit2['team']})
                    op += f"({rem2} {unit2['type']} {unit2['team']} left)"
                else:
                    op += f"({unit2['team']} {unit2['type']} eliminated)"

                # Indices idx1 and idx2 are now "used" because they were part of a battle.
                next_remaining_indices = tuple(sorted(list(set(remaining_indices) - {idx1, idx2})))

                # When battling, the units are not "added" to the `current_units` list in the same way.
                # Instead, the original units are consumed, and new *results* of the battle (if any remain)
                # are effectively what carries forward.
                # However, the problem states "Each unit can only go to one other unit. Such that you have a path that hits each group once."
                # This means we select two units from the `remaining_indices`, perform an operation, and then these two units are no longer `remaining`.
                # The units resulting from the battle are *new* units, not from the original `remaining_indices`.

                # So, the `next_state_units_for_recursion` should be:
                # 1. All units from `current_units` that were NOT idx1 or idx2.
                # 2. The potentially remaining units from the battle (if amount > 0).

                temp_units = []
                for k, u in enumerate(current_units):
                    if k != idx1 and k != idx2:
                        temp_units.append(u)

                if rem1 > 0:
                    temp_units.append({'type': unit1['type'], 'amount': rem1, 'team': unit1['team']})
                if rem2 > 0:
                    temp_units.append({'type': unit2['type'], 'amount': rem2, 'team': unit2['team']})

                advantage, path = find_best_path(tuple(temp_units), next_remaining_indices, path_so_far + [op])

                if advantage > max_advantage:
                    max_advantage = advantage
                    best_path_operations = path

    # If no operations can be performed with the remaining units (e.g., only one unit left),
    # calculate advantage from the current state and return.
    if not best_path_operations and len(remaining_indices) == len(current_units):
        # This means no valid pair could be formed or all original units have been processed.
        # This is the base case where we just evaluate the current advantage.
        advantage = calculate_blue_advantage(current_units)
        memo[state_key] = (advantage, path_so_far)
        return advantage, path_so_far

    memo[state_key] = (max_advantage, best_path_operations)
    return max_advantage, best_path_operations


def solve_unit_problem(json_data):
    """
    Solves the unit problem to maximize blue's advantage.
    """
    units = json.loads(json_data)

    # Assign a unique original index to each unit for tracking
    initial_units_with_indices = []
    for i, unit in enumerate(units):
        initial_units_with_indices.append({'original_index': i, **unit})

    # The `find_best_path` function needs to operate on a consistent representation of units.
    # We will pass the `initial_units_with_indices` as the `current_units` for the initial call,
    # and `remaining_indices` will refer to the `original_index`.

    # The `current_units` in `find_best_path` will be a list of *actual* units at that state,
    # which can include combined or post-battle units, but `remaining_indices` still refers to
    # the original indices that haven't been 'used' as part of an operation.

    # Initial call to the recursive function
    # `current_units` should be `units` as loaded from JSON
    # `remaining_indices` are the indices of all units initially

    # `find_best_path` should be initialized with the raw input units,
    # and `remaining_indices` will be a tuple of their original indices.
    # When a unit is used, its original index is removed from `remaining_indices`.
    # When a combined unit is formed, it's added to the list of `current_units` for the next state,
    # but it doesn't have an `original_index` that needs to be tracked by `remaining_indices`.

    initial_remaining_indices = tuple(range(len(units)))

    # Clear memoization cache for a new run
    memo.clear()

    max_advantage, best_path = find_best_path(tuple(units), initial_remaining_indices, [])

    return {
        "max_blue_advantage": max_advantage,
        "best_path_operations": best_path
    }


# Example Usage:
if __name__ == "__main__":
    example_json = """
    [
      { "type": "warriors", "amount": 12, "team": "red"},
      { "type": "archers", "amount": 7, "team": "blue"},
      { "type": "soldiers", "amount": 4, "team": "blue"},
      { "type": "typeless", "amount": 10, "team": "red"}
    ]
    """

    # This example expects: blue archers combine with blue soldiers, then fight red warriors.
    # 7 archers + 4 soldiers -> 11 archers (since 7 > 4, or 11 soldiers if 4 > 7, let's assume greater amount dictates type)
    # 7 archers + 4 soldiers (blue) -> 11 archers (blue)
    # Then, 11 archers (blue) vs 12 warriors (red)
    # 2 archers kill 3 warriors. So, 11 archers will kill (11/2)*3 = 16.5 warriors.
    # 12 warriors are killed, 0 red warriors left.
    # Remaining blue archers: 11 - (12/3)*2 = 11 - 8 = 3 archers left.
    # Blue advantage = 3.

    # Re-reading the combination rule: "they all turn into the unit there is more of".
    # 7 archers, 4 soldiers. Archers are more. So, 7+4 = 11 archers. Correct.

    result = solve_unit_problem(example_json)
    print(json.dumps(result, indent=2))

    print("\n--- Another Example ---")
    example_json_2 = """
    [
        {"type": "archers", "amount": 20, "team": "red"},
        {"type": "soldiers", "amount": 15, "team": "blue"},
        {"type": "warriors", "amount": 10, "team": "blue"}
    ]
    """
    # Expected optimal path:
    # 1. Blue Soldiers (15) combine with Blue Warriors (10) -> 25 Soldiers (since 15 > 10)
    # 2. 25 Soldiers (blue) fight 20 Archers (red)
    #    2 Soldiers kill 2 Archers. So, 25 soldiers kill 25 archers.
    #    Red Archers (20) are wiped out.
    #    Blue Soldiers remaining: 25 - 20 = 5.
    # Blue advantage: 5

    result_2 = solve_unit_problem(example_json_2)
    print(json.dumps(result_2, indent=2))

    print("\n--- Example with only one unit type on blue ---")
    example_json_3 = """
    [
        {"type": "archers", "amount": 50, "team": "red"},
        {"type": "soldiers", "amount": 20, "team": "red"},
        {"type": "warriors", "amount": 30, "team": "blue"}
    ]
    """
    # Blue warriors (30) vs Red archers (50)
    # Warriors kill soldiers. Archers kill warriors.
    # 2 Archers kill 3 Warriors. 50 archers kill (50/2)*3 = 75 warriors.
    # 30 warriors are killed.
    # Archers remaining: 50 - (30/3)*2 = 50 - 20 = 30.
    # Then Red soldiers (20) remaining.
    # Blue advantage: 0 - (30+20) = -50
    #
    # Blue warriors (30) vs Red soldiers (20)
    # 2 Warriors kill 2 Soldiers. 30 warriors kill 30 soldiers.
    # 20 soldiers are killed.
    # Warriors remaining: 30 - 20 = 10.
    # Then Red archers (50) remaining.
    # Blue advantage: 10 - 50 = -40
    # So, fighting soldiers first is better for blue.

    result_3 = solve_unit_problem(example_json_3)
    print(json.dumps(result_3, indent=2))