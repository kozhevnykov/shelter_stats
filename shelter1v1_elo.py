import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os, re
import operator
from datetime import datetime
from pprint import pprint


game_started = re.compile("((?:\d+\.?){3} \d+:\d+:\d+.\d) : Game started.*")
game_stopped = re.compile("((?:\d+\.?){3} \d+:\d+:\d+.\d) : Game stopped.*")
betterlogs = re.compile(
    "(?:\d+\.?){3} \d+:\d+:\d+.\d : 💡 BetterLogs: Joined player.* id: (\d+), name: (.*), ip: \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}, auth: (.+)")
betterlogs_geo = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : 💡 BetterLogs: Player .*")
chatline = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : .*#\d+ : .*")
team_win_match = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : (\w{3,4}) team won the match")
player_side = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : (.*) was moved to (\w{3,4})$")
goal_line = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : 📢 : (.+) Гол для (.*)! \| (.*)")

def results_to_sheet(df, worksheet=1):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/spreadsheets',
             'https://www.googleapis.com/auth/drive.file','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('shelter-elo-f89a18b95341.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open('UA PUB haxball statistics')
    sheet_instance = sheet.get_worksheet(worksheet)
    sheet_instance.clear()
    sheet_instance.insert_rows([[str(f'last update: {datetime.now()}')]] + [df.columns.values.tolist()] + df.values.tolist(), 1)
    sheet_instance.format("A2:H2", {
        "backgroundColor": {
            "red": 0.6,
            "green": 0.1,
            "blue": 0.0
        },
        "horizontalAlignment": "CENTER",
        "textFormat": {
            "foregroundColor": {
                "red": 1.0,
                "green": 1.0,
                "blue": 1.0
            },
            "fontSize": 10,
            "bold": True
        }
    })
    print(f'ELO worksheet {worksheet} updated')

def processing_nick(line):
    if betterlogs.match(line):
        nick = betterlogs.match(line).group(2).strip()
        auth = betterlogs.match(line).group(3)
        if auth not in players.keys():
            players[auth] = {nick: 1}
        else:
            if nick in players[auth].keys():
                players[auth][nick] += 1
            else:
                players[auth][nick] = 1

def starting_lineup(match):
    players = {'Red': [], 'Blue': []}
    for event in match:
        if game_started.match(event):
            break
        if player_side.match(event):
            players[player_side.match(event).group(2)].append(player_side.match(event).group(1).strip())
    return players

def match_result(match):
    for m in reversed(match):
        if team_win_match.match(m):
            if team_win_match.match(m).group(1) == "Red":
                return 1
            else:
                return 2

    goals = [0, 0]
    for line in match:
        if goal_line.match(line):
            if goal_line.match(line).group(1) == "🔵":
                goals[1] += 1
            else:
                goals[0] += 1
    if goals[0] > goals[1] and goals[0] >= 2:
        return 1
    elif goals[0] < goals[1] and goals[1] >= 2:
        return 2

    return 0

def get_stats(winner, players):
    player_stats = {p: {'wins': 0} for p in players['Red'] + players['Blue']}
    if winner > 0 and len(players['Red']) == 1 and len(players['Red']) == 1:
        if winner == 1:
            player_stats[players['Red'][0]]['wins'] += 1
        else:
            player_stats[players['Blue'][0]]['wins'] += 1
    else:
        return {'status': '!1v1'}

    player_stats_auth = {}
    for k, v in player_stats.items():
        if k in stack_players.keys():
            player_stats_auth[stack_players[k].strip()] = v
    return {'stats': player_stats_auth}

def analyse_match():
    match = current_match['logs']
    match_players = starting_lineup(match)
    match_winner = match_result(match)
    match_stats = get_stats(match_winner, match_players)
    current_match.update(match_stats)

def processing(line):
    global match_id, current_match, db_matches

    if not chatline.match(line) and not betterlogs.match(line) and not betterlogs_geo.match(line):
        current_match['logs'].append(line.strip())

    if game_stopped.match(line):
        current_match['status'] = 'stopped'
        current_match['stopped_at'] = datetime.strptime(game_stopped.match(line).group(1),
                                                        '%d.%m.%Y %H:%M:%S.%f')
        analyse_match()
        #del (current_match['logs'])
        if current_match['status'] == 'stopped':
            db_matches.append(current_match)
        match_id += 1
        current_match = {'status': 'init', 'id': match_id, 'logs': []}
    if game_started.match(line):
        current_match['status'] = 'in progress',
        current_match['start_at'] = datetime.strptime(game_started.match(line).group(1),
                                                      '%d.%m.%Y %H:%M:%S.%f')

    if betterlogs.match(line):
        processing_nick(line)
        nickname = betterlogs.match(line).group(2).strip()
        auth_key = betterlogs.match(line).group(3)
        stack_players[nickname] = auth_key

def get_users_from_players(players):
    users = {}
    for auth, nick_list in dict(sorted(players.items(),
                                       key=lambda item: sum(item[1].values()),
                                       reverse=True)).items():
        nick = max(nick_list.items(), key=operator.itemgetter(1))[0]
        if nick not in users.keys():
            users[nick] = {
                'idkeys': [auth],
                'visits': sum(nick_list.values()),
                'elo': [1000],
                }
        else:
            users[nick]['idkeys'].append(auth)
            users[nick]['visits'] += sum(nick_list.values())

    users_invert = {}
    for nick, data in users.items():
        for idkey in data['idkeys']:
            users_invert[idkey] = nick
    return users, users_invert

def get_stats_from_db_matches(db_matches):
    stats = {}
    for match in db_matches:
        for auth, match_stats in match['stats'].items():
            if auth not in stats.keys():
                stats[auth] = {
                    'matches': 1,
                    'wins': match_stats['wins'],
                }
            else:
                stats[auth]['matches'] += 1
                stats[auth]['wins'] += match_stats['wins']
    return stats

def elo_calc(match_stats, k=30):
    e1 = users[users_invert[match_stats[0][0]]]['elo'][-1]
    e2 = users[users_invert[match_stats[1][0]]]['elo'][-1]

    p1 = 1 / (1 + 10 ** ((e2 - e1) / 400))
    p2 = 1 / (1 + 10 ** ((e1 - e2) / 400))

    ne1 = e1 + k * (match_stats[0][1]['wins'] - p1)
    ne2 = e2 + k * (match_stats[1][1]['wins'] - p2)

    users[users_invert[match_stats[0][0]]]['elo'].append(round(ne1))
    users[users_invert[match_stats[1][0]]]['elo'].append(round(ne2))

    # print([e1,e2],[ne1,ne2], p1, p2, {match_stats[0][0], match_stats[1][0]})

def win_streak_calc(elos):
    base = 0
    current = 0
    if len(elos) > 1:
        for i in range(len(elos)-1):
            if elos[i] <= elos[i+1]:
                current += 1
            else:
                if base < current:
                    base = current
                current = 0
    return max(base, current)


if __name__ == '__main__':
    match_id = 0
    min_matches = 10
    current_match = {'status': '', 'id': -1, 'logs': []}
    db_matches = []
    stack_players = {}
    players = {}

    folder = 'vps-logs--ua-1-1--2/hax/out'
    for filename in [f for f in sorted(os.listdir(folder)) if f >= 'out__2024-04-01_23-59-00.log'] + ['out.log']:
        f = os.path.join(folder, filename)
        if filename == '.DS_Store':
            continue
        with open(f, 'r', encoding='utf-8') as file:
            for line in file:
                processing(line)
    print(f'ALL matches - {len(db_matches)}, players - {len(players)}')

    stats = get_stats_from_db_matches(db_matches)
    users, users_invert = get_users_from_players(players)
    blacklist = {'Vh2iYyJEP3DxxnmDTBwMe1fxbm47EhbttdHEsUVaIOA': 'l1ch'}

    # calculating elo for each match
    for i in range(len(db_matches)):
        m = db_matches[i]
        good_match = True
        if len(m['stats'].keys()) != 2:
            good_match = False
        for auth in m['stats'].keys():
            if auth not in users_invert.keys() or stats[auth]['matches'] < min_matches or auth in blacklist.keys():
                good_match = False
            # if auth == 'nzaKskHI':
            #     pprint.pprint(m)
        if good_match:
            db_matches[i]['status'] = 'ELO stopped'
            for idkey in db_matches[i]['stats']:
                db_matches[i]['stats'][idkey]['elo_begin'] = users[users_invert[idkey]]['elo'][-1]
            elo_calc(list(m['stats'].items()))
            for idkey in db_matches[i]['stats']:
                db_matches[i]['stats'][idkey]['elo_end'] = users[users_invert[idkey]]['elo'][-1]
                db_matches[i]['stats'][idkey]['elo_diff'] = (db_matches[i]['stats'][idkey]['elo_end'] -
                                                             db_matches[i]['stats'][idkey]['elo_begin'])

    for user in users:
        users[user]['NICK'] = user
        users[user]['ELO'] = users[user]['elo'][-1]
        users[user]['matches'] = len(users[user]['elo']) - 1
        users[user]['ALL matches'] = 0
        users[user]['wins'] = 0
        users[user]['win-streak'] = win_streak_calc(users[user]['elo'])
        for idkey in users[user]['idkeys']:
            if idkey in stats.keys():
                users[user]['ALL matches'] += stats[idkey]['matches']
                users[user]['wins'] += stats[idkey]['wins']
        if users[user]['ALL matches'] > 0:
            users[user]['WR %'] = users[user]['wins'] / users[user]['ALL matches']
        else:
            users[user]['WR %'] = None

    df = pd.DataFrame(users).T.sort_values(by=['ELO'], ascending=False)
    df = df[['NICK','ELO', 'matches', 'WR %', 'win-streak']]

    df_elo_matches = pd.DataFrame({'id':[], 'started_at': [],
                        'p1': [], 'p1_elo_begin': [], 'p1_elo_diff': [],
                        'p2': [], 'p2_elo_begin': [], 'p2_elo_diff': []})
    for m in db_matches:
        if m['status'] == 'ELO stopped':
            df_elo_matches.loc[len(df_elo_matches)] = [m['id'], m['start_at'].strftime('%d.%m.%Y %H'),
                            users[users_invert[list(m['stats'].keys())[0]]]['NICK'],
                            m['stats'][list(m['stats'].keys())[0]]['elo_begin'],
                            m['stats'][list(m['stats'].keys())[0]]['elo_diff'],
                            users[users_invert[list(m['stats'].keys())[1]]]['NICK'],
                            m['stats'][list(m['stats'].keys())[1]]['elo_begin'],
                            m['stats'][list(m['stats'].keys())[1]]['elo_diff']]

    df_elo_matches = df_elo_matches.sort_values(by=['id'], ignore_index=True, ascending=False)

    results_to_sheet(df[df['matches'] >= min_matches], worksheet=1)
    results_to_sheet(df_elo_matches, worksheet=2)

    # import json
    # with open("dataHAX/elo1x1.json", 'w') as file:
    #     json.dump(db_matches, file, indent=4)

    # import matplotlib.pyplot as plt
    # plt.plot(users['111']['elo'])
    # plt.show()

    #df_temp.drop(columns='elo').sort_values(by=['ELO_matches'], ascending=False).to_csv('dataHAX/elo.csv')