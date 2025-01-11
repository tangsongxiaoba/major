import random
import json

def order(n):
    li = [0 for _ in range(n)]
    vis = [0 for _ in range(n+1)]
    res = []

    def dfs(x):
        if x > n/2:
            res.append(li[:])
            return
        a = 0
        for i in range(1, n+1):
            if vis[i] == 0:
                vis[i], a = 1, i
                break
        for b in range(n, 0, -1):
            if vis[b] == 1:
                continue
            li[a-1], li[b-1], vis[b] = b, a, 1
            dfs(x+1)
            li[a-1], li[b-1], vis[b] = 0, 0, 0
        vis[a] = 0

    dfs(1)
    res = sorted(res, key=lambda x: -(x[0]+x[1]+x[2]))
    return res

ORDER_6 = order(6)
ORDER_8 = order(8)

names_set = set()

def run(teams):

    # init
    diff = [0 for _ in range(17)]
    oppo = [[] for _ in range(17)]
    table = [[[] for _ in range(6)] for _ in range(6)]
    final_res = ""
    for i in range(16):
        table[0][0].append(teams[f"team_{i+1}"])

    def res(winner, loser):

        def add(team, opponent):
            if opponent not in oppo[team["init_seed"]]:
                oppo[team["init_seed"]].append(opponent)
            else:
                print(f"Duplicated {opponent} in {team}")
                exit(-1)

        add(winner, loser)
        add(loser, winner)

    def match(team_a, team_b):
        value_a = team_a['battle_value'] * random.uniform(team_a["l_factor"], team_a["r_factor"])
        value_b = team_b['battle_value'] * random.uniform(team_b["l_factor"], team_b["r_factor"])
        result = 0
        if value_a > value_b:
            result = 1
        elif value_a < value_b:
            result = -1
        else:
            result = random.choice([1, -1])
        winner = None
        loser = None
        if result == 1:
            winner = team_a
            loser = team_b
        else:
            winner = team_b
            loser = team_a
        res(winner, loser)
        return winner, loser
    
    def match3(team_a, team_b):
        cnt_a, cnt_b = 0, 0
        for _ in range(3):
            value_a = team_a['battle_value'] * random.uniform(team_a["l_factor"], team_a["r_factor"])
            value_b = team_b['battle_value'] * random.uniform(team_b["l_factor"], team_b["r_factor"])
            result = 0
            if value_a > value_b:
                result = 1
            elif value_a < value_b:
                result = -1
            else:
                result = random.choice([1, -1])
            if result == 1:
                cnt_a += 1
            else:
                cnt_b += 1
            if cnt_a == 2 or cnt_b == 2:
                break
        winner = None
        loser = None
        if cnt_a > cnt_b:
            winner = team_a
            loser = team_b
        else:
            winner = team_b
            loser = team_a
        res(winner, loser)
        return winner, loser

    _ROUND = [[],
              [(1,0),(0,1)],
              [(2,0),(1,1),(0,2)],
              [(3,0),(2,1),(1,2),(0,3)],
              [(3,0),(3,1),(2,2),(1,3),(0,3)],
              [(3,0),(3,1),(3,2),(2,3),(1,3),(0,3)]]

    def update(round):

        def find(opponent):
            for x, y in _ROUND[round]:
                if opponent in table[x][y]:
                    return x, y
            for x, y in _ROUND[round]:
                print(f"{x}-{y}: ", table[x][y])
            print(f"{2}-{2}: ", table[2][2])
            return -1, -1
        
        for x, y in _ROUND[round]:
            for team in table[x][y]:
                diff[team["init_seed"]] = 0
                for opponent in oppo[team["init_seed"]]:
                    xx, yy = find(opponent)
                    if xx == -1 or yy == -1:
                        print(f"Error encountered when finding {opponent}...")
                        print(round)
                        exit(-1)
                    diff[team["init_seed"]] += xx - yy

    # Round 1
    # 0~7 -> 1~8 <-> 9~16 <- 8~15
    for i in range(8):
        winner, loser = match(table[0][0][i], table[0][0][i+8])
        table[1][0].append(winner)
        table[0][1].append(loser)
    update(1)

    # 1-0
    # first keyword: difficulty score(descending). second keyword: initial_seed(ascending).
    table[1][0] = sorted(table[1][0], key=lambda x: (-diff[x["init_seed"]], x["init_seed"]))
    # 0-1
    table[0][1] = sorted(table[0][1], key=lambda x: (-diff[x["init_seed"]], x["init_seed"]))
    
    # Round 2
    # 0-7, 1-6, 2-5, 3-4
    for i in range(4):
        winner, loser = match(table[1][0][i], table[1][0][7-i])
        table[2][0].append(winner)
        table[1][1].append(loser)
        winner, loser = match(table[0][1][i], table[0][1][7-i])
        table[1][1].append(winner)
        table[0][2].append(loser)
    update(2)

    table[2][0] = sorted(table[2][0], key=lambda x: (-diff[x["init_seed"]], x["init_seed"]))
    table[1][1] = sorted(table[1][1], key=lambda x: (-diff[x["init_seed"]], x["init_seed"]))
    table[0][2] = sorted(table[0][2], key=lambda x: (-diff[x["init_seed"]], x["init_seed"]))
    
    # Round 3
    # 2-0 / 0-2: 0-3, 1-2
    for i in range(2):
        winner, loser = match3(table[2][0][i], table[2][0][3-i])
        table[3][0].append(winner)
        table[2][1].append(loser)
        winner, loser = match3(table[0][2][i], table[0][2][3-i])
        table[1][2].append(winner)
        table[0][3].append(loser)
    # 1-1: 0-7, ... (0-6 when faced rematch)
    flags = [0 for _ in range(8)]
    for j in range(105):
        for i in range(8):
            k = ORDER_8[j][i]-1
            if (not flags[k]) and (not flags[i]) and (table[1][1][k] not in oppo[table[1][1][i]["init_seed"]]):
                flags[k] = i+1
                flags[i] = k+1
        if 0 in flags:
            flags = [0 for _ in range(8)]
            continue
        for i in range(8):
            k = ORDER_8[j][i]-1
            if (table[1][1][k] not in oppo[table[1][1][i]["init_seed"]]):
                winner, loser = match3(table[1][1][i], table[1][1][k])
                table[2][1].append(winner)
                table[1][2].append(loser)
        break
    if 0 in flags:
        print(f"1-1 {table[1][1]} cannot find suitable oppponent...")
        exit(-1)
    update(3)

    table[3][0] = sorted(table[3][0], key=lambda x: (-diff[x["init_seed"]], x["init_seed"]))
    table[2][1] = sorted(table[2][1], key=lambda x: (-diff[x["init_seed"]], x["init_seed"]))
    table[1][2] = sorted(table[1][2], key=lambda x: (-diff[x["init_seed"]], x["init_seed"]))
    table[0][3] = sorted(table[0][3], key=lambda x: (-diff[x["init_seed"]], x["init_seed"]))

    # Round 4
    # 2-1
    flags = [0 for _ in range(6)]
    for j in range(15):
        for i in range(6):
            k = ORDER_6[j][i]-1
            if (not flags[k]) and (not flags[i]) and (table[2][1][k] not in oppo[table[2][1][i]["init_seed"]]):
                flags[k] = i+1
                flags[i] = k+1
        if 0 in flags:
            flags = [0 for _ in range(6)]
            continue
        for i in range(6):
            k = ORDER_6[j][i]-1
            if (table[2][1][k] not in oppo[table[2][1][i]["init_seed"]]):
                winner, loser = match3(table[2][1][i], table[2][1][k])
                table[3][1].append(winner)
                table[2][2].append(loser)
        break
    if 0 in flags:
        print(f"2-1 {table[2][1]} cannot find suitable oppponent...")
        exit(-1)
    # 1-2
    flags = [0 for _ in range(6)]
    for j in range(15):
        for i in range(6):
            k = ORDER_6[j][i]-1
            if (not flags[k]) and (not flags[i]) and (table[1][2][k] not in oppo[table[1][2][i]["init_seed"]]):
                flags[k] = i+1
                flags[i] = k+1
        if 0 in flags:
            flags = [0 for _ in range(6)]
            continue
        for i in range(6):
            k = ORDER_6[j][i]-1
            if (table[1][2][k] not in oppo[table[1][2][i]["init_seed"]]):
                winner, loser = match3(table[1][2][i], table[1][2][k])
                table[2][2].append(winner)
                table[1][3].append(loser)
        break
    if 0 in flags:
        print(f"1-2 {table[1][2]} cannot find suitable oppponent...")
        exit(-1)
    update(4)

    table[3][1] = sorted(table[3][1], key=lambda x: (-diff[x["init_seed"]], x["init_seed"]))
    table[2][2] = sorted(table[2][2], key=lambda x: (-diff[x["init_seed"]], x["init_seed"]))
    table[1][3] = sorted(table[1][3], key=lambda x: (-diff[x["init_seed"]], x["init_seed"]))

    # Round 5
    # 2-2
    flags = [0 for _ in range(6)]
    for j in range(15):
        for i in range(6):
            k = ORDER_6[j][i]-1
            if (not flags[k]) and (not flags[i]) and (table[2][2][k] not in oppo[table[2][2][i]["init_seed"]]):
                flags[k] = i+1
                flags[i] = k+1
        if 0 in flags:
            flags = [0 for _ in range(6)]
            continue
        for i in range(6):
            k = ORDER_6[j][i]-1
            if (table[2][2][k] not in oppo[table[2][2][i]["init_seed"]]):
                winner, loser = match3(table[2][2][i], table[2][2][k])
                table[3][2].append(winner)
                table[2][3].append(loser)
        break
    if 0 in flags:
        print(f"2-2 {table[2][2]} cannot find suitable oppponent...")
        print(flags)
        exit(-1)
    update(5)

    table[3][2] = sorted(table[3][2], key=lambda x: (-diff[x["init_seed"]], x["init_seed"]))
    table[2][3] = sorted(table[2][3], key=lambda x: (-diff[x["init_seed"]], x["init_seed"]))
    
    name_3_0 = []
    name_3_0.append(table[3][0][0]["name"])
    name_3_0.append(table[3][0][1]["name"])
    name_3_0 = sorted(name_3_0)
    name_3_12 = []
    for i in range(1, 3):
        for j in table[3][i]:
            name_3_12.append(j["name"])
    name_3_12 = sorted(name_3_12)
    name_0_3 = []
    name_0_3.append(table[0][3][0]["name"])
    name_0_3.append(table[0][3][1]["name"])
    name_0_3 = sorted(name_0_3)

    names = []
    names.extend(name_3_0)
    names.extend(name_3_12)
    names.extend(name_0_3)

    names_table = [[sorted([table[x][y][z]["name"] for z in range(len(table[x][y]))]) for y in range(4)] for x in range(4)]

    # names_set.add(json.dumps(names_table))

    for name in names:
        final_res += name + " "

    return final_res, names_table
    # return json.dumps(names_table)

# with open("teams.json", "w", encoding="utf-8") as f:
#     f.write(json.dumps(teams))

with open("teams.json", "r", encoding="utf-8") as f:
    teams = json.load(f)

cnt = {}

rec = {}

for i in range(1, 10000000 + 1):
    if i % 10000 == 0:
        print(f"simulated {i} times...")
    res, table = run(teams)
    if res not in cnt:
        cnt[res] = 1
        rec[res] = table
    else:
        cnt[res] += 1

ans = sorted(cnt.items(), key=lambda x:(-x[1], x[0]))[:10]
i = 0
for x, y in ans:
    print(x, y)
    with open(f"results_{i}.json", "w") as f:
        f.write(json.dumps(rec[x]))
    i += 1