#!/usr/bin/env python3
import itertools

# —————————————————————————————————————————————————————————————
#  DEFINE YOUR “INLINE” JSON HERE:
#  A list of {type, amount, team} dicts.
# —————————————————————————————————————————————————————————————
groups = [
    {"type": "warriors", "amount": 12, "team": "red"},
    {"type": "archers",  "amount":  7, "team": "blue"},
    {"type": "soldiers", "amount":  4, "team": "blue"},
]


# —————————————————————————————————————————————————————————————
#  CONFIGURE YOUR “ROCK-PAPER-SCISSORS” KILL RATES HERE
#  kill_rates[(attacker_type, defender_type)] = (units_required, kills_done)
# —————————————————————————————————————————————————————————————
kill_rates = {
    ('archers',  'warriors'): (2, 3),
    ('warriors', 'soldiers'): (2, 3),
    ('soldiers','archers'):   (2, 2),
    # same-type or typeless vs anything → no net kills
}


def simulate_path(groups, path):
    """
    Simulate one fixed ordering of groups:
      – if the next group is same-team: COMBINE
      – otherwise: FIGHT (attacker only kills; no defender casualties accounted)
    Returns (score, survivors_dict).
    """
    # Copy initial amounts
    surv = {i: g['amount'] for i, g in enumerate(groups)}

    # Start with first group in the path
    cur = path[0]
    cur_type = groups[cur]['type']
    cur_team = groups[cur]['team']

    for nxt in path[1:]:
        if surv[cur] <= 0:
            break
        if surv[nxt] <= 0:
            continue

        if groups[nxt]['team'] == cur_team:
            # ——— COMBINE
            a = surv[cur]
            b = surv[nxt]
            total = a + b
            new_type = cur_type if a >= b else groups[nxt]['type']
            surv[cur] = total
            surv[nxt] = 0
            cur_type = new_type

        else:
            # ——— FIGHT
            key = (cur_type, groups[nxt]['type'])
            if key in kill_rates:
                req, kills = kill_rates[key]
                rounds = surv[cur] // req
                dead = rounds * kills
                surv[nxt] = max(0, surv[nxt] - dead)
            # no back‐kill

    # Compute score = blue_total − red_total
    blue_left = sum(s for i, s in surv.items() if groups[i]['team'] == 'blue')
    red_left  = sum(s for i, s in surv.items() if groups[i]['team'] == 'red')
    return blue_left - red_left, surv


def find_best_path(groups):
    n = len(groups)
    best_score = None
    best_path = None

    for start in range(n):
        rest = list(range(n))
        rest.remove(start)
        for perm in itertools.permutations(rest):
            path = [start] + list(perm)
            score, _ = simulate_path(groups, path)
            if best_score is None or score > best_score:
                best_score = score
                best_path = path

    return best_score, best_path


def main():
    best_score, best_path = find_best_path(groups)
    print(f"\nBest score (blue_survivors – red_survivors): {best_score}\n")
    print("Best path:")
    for idx in best_path:
        g = groups[idx]
        print(f"  • {g['team'].upper():4} | {g['amount']:3}× {g['type']}")

    # Detailed survivors
    _, survivors = simulate_path(groups, best_path)
    print("\nFinal survivors by group:")
    for idx in best_path:
        g = groups[idx]
        print(f"  • {g['team'].upper():4} | {survivors[idx]:3}× {g['type']}")
    print()


if __name__ == "__main__":
    main()



