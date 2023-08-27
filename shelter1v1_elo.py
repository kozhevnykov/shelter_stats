import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import re
import operator
from datetime import datetime

game_started = re.compile("((?:\d+\.?){3} \d+:\d+:\d+.\d) : Game started")
game_stopped = re.compile("((?:\d+\.?){3} \d+:\d+:\d+.\d) : Game stopped")
betterlogs = re.compile(
    "(?:\d+\.?){3} \d+:\d+:\d+.\d : 💡 BetterLogs: Joined player.* id: (\d+), name: (.*), ip: \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}, auth: (.+)")
chatline = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : .*#\d+ : .*")
team_win_match = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : (\w{3,4}) team won the match")
player_side = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : (.*) was moved to (\w{3,4})$")

def results_to_sheet(df):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/spreadsheets',
             'https://www.googleapis.com/auth/drive.file','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('shelter-elo-f89a18b95341.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open('Shelter stats')
    sheet_instance = sheet.get_worksheet(1)
    sheet_instance.clear()
    sheet_instance.insert_rows([df.columns.values.tolist()] + (df.values.tolist()), 1)

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
    winner = 0
    for m in reversed(match):
        if team_win_match.match(m):
            if team_win_match.match(m).group(1) == "Red":
                winner = 2
            else:
                winner = 1
            break
    return winner

def get_stats(winner, players, m):
    player_stats = {p: {'wins': 0} for p in players['Red'] + players['Blue']}
    # TODO: add condition when match not over properly
    if winner > 0 and len(players['Red']) == 1:
        if winner == 1:
            player_stats[players['Red'][0]]['wins'] += 1
        else:
            player_stats[players['Blue'][0]]['wins'] += 1

        # goals = get_goals(m, players['Red'] + players['Blue'])
        # for p in goals.keys():
        #     player_stats[p]['goals'] += goals[p]
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
    match_stats = get_stats(match_winner, match_players, match)
    current_match.update(match_stats)

def processing(line):
    global match_id, current_match, db_matches

    if not chatline.match(line) and not betterlogs.match(line):
        current_match['logs'].append(line.strip())

    if game_stopped.match(line):
        current_match['status'] = 'stopped'
        current_match['stopped_at'] = datetime.strptime(game_stopped.match(line).group(1),
                                                        '%d.%m.%Y %H:%M:%S.%f')
        analyse_match()
        del (current_match['logs'])
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

def ELO_calc(match_stats):
    K = 30
    for auth, stats in match_stats:
        if 'elo' not in users[users_invert[auth]].keys():
            users[users_invert[auth]]['elo'] = [1000]
        if stats['wins'] == 1:
            win_elo = users[users_invert[auth]]['elo'][-1]
        else:
            lose_elo = users[users_invert[auth]]['elo'][-1]

    E = 1 / (1 + 10 ** ((lose_elo - win_elo) / 400))
    #print(E, win_elo, lose_elo)

    for auth, stats in match_stats:
        if stats['wins'] == 1:
            users[users_invert[auth]]['elo'].append(round(users[users_invert[auth]]['elo'][-1] + K * (1 - E)))
        else:
            users[users_invert[auth]]['elo'].append(round(users[users_invert[auth]]['elo'][-1] + K * (0 - E)))

    #print(K * (1 - E), K * (0 - E))


if __name__ == '__main__':
    match_id = 0
    current_match = {'status': '', 'id': -1, 'logs': []}
    db_matches = []
    stack_players = {}
    players = {}

    folder = 'vps-logs--ua-1-1--2/hax/out'
    for filename in [f for f in sorted(os.listdir(folder)) if f > 'out__2023-08-21_23-59-00.log']:
        f = os.path.join(folder, filename)
        if filename == '.DS_Store':
            continue
        with open(f, 'r', encoding='utf-8') as file:
            for line in file:
                processing(line)

    print(len(db_matches), len(players))

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
    # players = players['8zC-sxowXUIMFKZ2seldvc1vegZo'] = {'Roll.': 6, 'osa': 1,}
    # db_matches = [...]

    users = {}
    for k, v in dict(sorted(players.items(), key=lambda item: sum(item[1].values()),
                            reverse=True)).items():
        if max(v.items(), key=operator.itemgetter(1))[0] not in users.keys():
            users[max(v.items(), key=operator.itemgetter(1))[0]] = {
                'idkeys': [k],
                'visits': sum(v.values())}
        else:
            users[max(v.items(), key=operator.itemgetter(1))[0]]['idkeys'].append(k)
            users[max(v.items(), key=operator.itemgetter(1))[0]]['visits'] += sum(v.values())
        if sum(v.values()) < 2:
            break

    users_invert = {}
    for nick, data in users.items():
        for idkey in data['idkeys']:
            users_invert[idkey] = nick

    for match in db_matches:
        flag = True
        if len(match['stats'].keys()) == 2:
            for auth in match['stats'].keys():
                if auth not in users_invert.keys():
                    flag = False
                    break
            if flag:
                ELO_calc(match['stats'].items())

    for k in stats.keys():
        try:
            stats[k]['elo'] = users[users_invert[k]]['elo'][-1]
            stats[k]['nick'] = users_invert[k]
            stats[k]['win-rate %'] = stats[k]['wins'] / stats[k]['matches']
        except:
            pass

    import pandas as pd
    df = pd.DataFrame(stats).T.sort_values(by=['elo'], ascending=False, ignore_index=True)
    df = df[['nick', 'elo', 'matches', 'win-rate %']]
    #results_to_sheet(df[df['elo'] > 0 ])

import pprint
pprint.pprint(db_matches)

for match in db_matches:
    print(match['id'], match['stats'])


