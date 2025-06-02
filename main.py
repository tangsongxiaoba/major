from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from copy import deepcopy
import math
import random
import pprint

def load_teams(filename='teams.json'):
    with open(filename, 'r', encoding='utf-8') as f:
        teams_dict = json.load(f)
    teams = []
    for k, v in teams_dict.items():
        teams.append({
            'id': k,
            'name': v['name'],
            'init_seed': v['init_seed'],
            'battle_value': v['battle_value'],
        })
    return teams

def min_max_normalize(teams):
    values = [t['battle_value'] for t in teams]
    vmin, vmax = min(values), max(values)
    for t in teams:
        t['battle_norm'] = (t['battle_value'] - vmin) / (vmax - vmin) if vmax != vmin else 0.0
    return teams

def win_prob(battle_norm_a, battle_norm_b):
    diff = battle_norm_a - battle_norm_b
    prob = 1 / (1 + math.exp(-diff))
    prob = max(0.05, min(prob, 0.95))
    return prob

def major_swiss_initial_pairings(teams):
    teams = sorted(teams, key=lambda x: x['init_seed'])
    pair_idx = [
        (1, 9), (2, 10), (3, 11), (4, 12),
        (5, 13), (6, 14), (7, 15), (8, 16)
    ]
    pairings = []
    for a, b in pair_idx:
        pairings.append((teams[a-1], teams[b-1]))
    return pairings

PAIR_PRIORITY_TABLE = [
    [(1,6),(2,5),(3,4)],
    [(1,6),(2,4),(3,5)],
    [(1,5),(2,6),(3,4)],
    [(1,5),(2,4),(3,6)],
    [(1,4),(2,6),(3,5)],
    [(1,4),(2,5),(3,6)],
    [(1,6),(2,3),(4,5)],
    [(1,5),(2,3),(4,6)],
    [(1,3),(2,6),(4,5)],
    [(1,3),(2,5),(4,6)],
    [(1,4),(2,3),(5,6)],
    [(1,3),(2,4),(5,6)],
    [(1,2),(3,6),(4,5)],
    [(1,2),(3,5),(4,6)],
    [(1,2),(3,4),(5,6)],
]

def sort_group_by_seed(group):
    return sorted(group, key=lambda x: x['init_seed'])

def get_current_buchholz(team, teams):
    score = 0
    for opp_name in team['history']:
        opp = next(filter(lambda t: t['name'] == opp_name, teams))
        score += opp['W'] - opp['L']
    return score

def re_seed(group, all_teams):
    for t in group:
        t['buchholz'] = get_current_buchholz(t, all_teams)
    return sorted(group, key=lambda x: (-x['W'], x['L'], -t['buchholz'], t['init_seed']))

def get_priority_pairing(group, history):
    n = len(group)
    if n < 2:
        return []
    if n == 2:
        a, b = group
        if (a['name'], b['name']) in history or (b['name'], a['name']) in history:
            return []
        else:
            return [(a, b)]
    if n > 6:
        p1 = get_priority_pairing(group[:6], history)
        p2 = get_priority_pairing(group[6:], history)
        return p1 + p2

    idx_to_team = [None] + group
    for pattern in PAIR_PRIORITY_TABLE:
        used = set()
        pairs = []
        valid = True
        for (i,j) in pattern:
            if i > n or j > n or i in used or j in used:
                valid = False
                break
            a, b = idx_to_team[i], idx_to_team[j]
            if (a['name'], b['name']) in history or (b['name'], a['name']) in history:
                valid = False
                break
            pairs.append((a,b))
            used.add(i)
            used.add(j)
        if valid and len(used) == n:
            return pairs

    used = set()
    pairs = []
    for i in range(n):
        if i in used:
            continue
        for j in range(i+1, n):
            if j in used:
                continue
            a, b = group[i], group[j]
            if (a['name'], b['name']) not in history and (b['name'], a['name']) not in history:
                pairs.append((a,b))
                used.add(i)
                used.add(j)
                break
    return pairs

def simulate_match(team_a, team_b):
    prob_a = win_prob(team_a['battle_norm'], team_b['battle_norm'])
    if random.random() < prob_a:
        return team_a, team_b
    else:
        return team_b, team_a

def simulate_swiss_stage_once(teams_src):
    teams = deepcopy(teams_src)
    for t in teams:
        t['W'], t['L'] = 0, 0
        t['history'] = []
    history = set()
    round_num = 0
    while True:
        round_num += 1
        active_teams = [t for t in teams if t['W'] < 3 and t['L'] < 3]
        if not active_teams or all(t['W'] == 3 or t['L'] == 3 for t in teams):
            break

        pairings = []
        if round_num == 1:
            pairings = major_swiss_initial_pairings(teams)
        else:
            groups = {}
            for t in teams:
                key = (t['W'], t['L'])
                if t['W'] < 3 and t['L'] < 3:
                    groups.setdefault(key, []).append(t)
            for key in sorted(groups.keys(), reverse=True):
                group = groups[key]
                group = re_seed(group, teams)
                pairs = get_priority_pairing(group, history)
                pairings.extend(pairs)
            paired = set(a['name'] for a,b in pairings) | set(b['name'] for a,b in pairings)
            remain = [t for t in active_teams if t['name'] not in paired]
            while len(remain) >= 2:
                a = remain.pop()
                b = remain.pop()
                pairings.append((a, b))

        for a, b in pairings:
            win, lose = simulate_match(a, b)
            win['W'] += 1
            lose['L'] += 1
            win['history'].append(lose['name'])
            lose['history'].append(win['name'])
            history.add((win['name'], lose['name']))

    result = []
    for t in sorted(teams, key=lambda x: x['init_seed']):
        result.append((t['name'], t['W'], t['L']))
    return tuple(result)

def simulate_batch_and_stats(teams, batch_n):
    combo_counter_3_0 = Counter()
    combo_counter_3_1_2 = Counter()
    combo_counter_0_3 = Counter()   # 新增
    for _ in range(batch_n):
        res = simulate_swiss_stage_once(teams)

        group_3_0 = []
        group_3_1_2 = []
        group_0_3 = []   # 新增
        for name, W, L in res:
            if W == 3 and L == 0:
                group_3_0.append(name)
            elif W == 3 and (L == 1 or L == 2):
                group_3_1_2.append(name)
            elif W == 0 and L == 3:
                group_0_3.append(name)   # 新增

        if len(group_3_0) == 2:
            combo_counter_3_0[tuple(sorted(group_3_0))] += 1
        if len(group_3_1_2) == 6:
            combo_counter_3_1_2[tuple(sorted(group_3_1_2))] += 1
        if len(group_0_3) == 2:   # 新增
            combo_counter_0_3[tuple(sorted(group_0_3))] += 1
    return combo_counter_3_0, combo_counter_3_1_2, combo_counter_0_3   # 新增

def multi_simulate_with_combo_stats(n_sim, teams, n_workers=8, batch_size=100_000):
    total_combo_3_0 = Counter()
    total_combo_3_1_2 = Counter()
    total_combo_0_3 = Counter()   # 新增
    n_batches = n_sim // batch_size
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = []
        for _ in range(n_batches):
            futures.append(executor.submit(simulate_batch_and_stats, teams, batch_size))
        finished = 0
        total = n_batches
        for f in as_completed(futures):
            c3, c6, c0 = f.result()   # 注意接收新增的返回值
            total_combo_3_0 += c3
            total_combo_3_1_2 += c6
            total_combo_0_3 += c0   # 新增
            finished += 1
            if finished % max(1, total//100) == 0 or finished == total:
                print(f"\r模拟中: {finished}/{total} 批次完成", end='', flush=True)
        print()
    return total_combo_3_0, total_combo_3_1_2, total_combo_0_3   # 新增

if __name__ == '__main__':
    teams = load_teams('teams.json')
    teams = min_max_normalize(teams)
    n_sim = 10000000
    n_workers = 16
    batch_size = 1000
    print(f"开始模拟，共{n_sim}次...")
    total_combo_3_0, total_combo_3_1_2, total_combo_0_3 = multi_simulate_with_combo_stats(n_sim, teams, n_workers, batch_size)

    if total_combo_3_0:
        combo, cnt = total_combo_3_0.most_common(1)[0]
        print(f"\n3-0晋级概率最高的组合：{' + '.join(combo)}，出现次数 {cnt}/{n_sim}，概率 {cnt/n_sim*100:.2f}%")
    else:
        print("\n没有发现完整的两队3-0晋级组合（样本太少？）")

    if total_combo_3_1_2:
        combo6, cnt6 = total_combo_3_1_2.most_common(1)[0]
        print(f"\n3-1/3-2晋级概率最高的六支队伍组合：{' + '.join(combo6)}，出现次数 {cnt6}/{n_sim}，概率 {cnt6/n_sim*100:.2f}%")
    else:
        print("\n没有发现完整的六队3-1/3-2晋级组合（样本太少？）")

    # 新增部分
    if total_combo_0_3:
        combo03, cnt03 = total_combo_0_3.most_common(1)[0]
        print(f"\n0-3出局概率最高的组合：{' + '.join(combo03)}，出现次数 {cnt03}/{n_sim}，概率 {cnt03/n_sim*100:.2f}%")
    else:
        print("\n没有发现完整的两队0-3出局组合（样本太少？）")
