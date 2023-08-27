import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os, re
import operator
from datetime import datetime
import pprint


game_started = re.compile("((?:\d+\.?){3} \d+:\d+:\d+.\d) : Game started")
game_stopped = re.compile("((?:\d+\.?){3} \d+:\d+:\d+.\d) : Game stopped")
betterlogs = re.compile(
    "(?:\d+\.?){3} \d+:\d+:\d+.\d : 💡 BetterLogs: Joined player.* id: (\d+), name: (.*), ip: \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}, auth: (.+)")
betterlogs_geo = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : 💡 BetterLogs: Player .*")
chatline = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : .*#\d+ : .*")
team_win_match = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : (\w{3,4}) team won the match")
player_side = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : (.*) was moved to (\w{3,4})$")
goal_line = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : 📢 : (.+) Гол для (.*)! \| (.*)")

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
    if goals[0] > goals[1]:
        return 1
    elif goals[0] < goals[1]:
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


def ELO_calc(match_stats, k=30):
    e1 = users[users_invert[match_stats[0][0]]]['elo'][-1]
    e2 = users[users_invert[match_stats[1][0]]]['elo'][-1]

    p1 = 1 / (1 + 10 ** ((e2 - e1) / 400))
    p2 = 1 / (1 + 10 ** ((e1 - e2) / 400))

    ne1 = e1 + k * (match_stats[0][1]['wins'] - p1)
    ne2 = e2 + k * (match_stats[1][1]['wins'] - p2)

    users[users_invert[match_stats[0][0]]]['elo'].append(round(ne1))
    users[users_invert[match_stats[1][0]]]['elo'].append(round(ne2))

    # print([e1,e2],[ne1,ne2], p1, p2, {match_stats[0][0], match_stats[1][0]})


if __name__ == '__main__':
    match_id = 0
    current_match = {'status': '', 'id': -1, 'logs': []}
    db_matches = []
    stack_players = {}
    players = {}

    folder = 'vps-logs--ua-1-1--2/hax/out'
    for filename in [f for f in sorted(os.listdir(folder)) if f >= 'out__2023-08-21_23-59-00.log']:
        f = os.path.join(folder, filename)
        if filename == '.DS_Store':
            continue
        with open(f, 'r', encoding='utf-8') as file:
            for line in file:
                processing(line)

    print(f' matches - {len(db_matches)}, players - {len(players)}')

    stats = get_stats_from_db_matches(db_matches)
    users, users_invert = get_users_from_players(players)

    # calculating elo for each match
    for match in db_matches:
        good_match = True
        if len(match['stats'].keys()) != 2:
            good_match = False
        for auth in match['stats'].keys():
            if auth not in users_invert.keys():
                good_match = False
            if stats[auth]['matches'] < 5:
                good_match = False
        if good_match:
            ELO_calc(list(match['stats'].items()))


    for auth in stats.keys():
        stats[auth]['ELO'] = users[users_invert[auth]]['elo'][-1]
        stats[auth]['NICK'] = users_invert[auth]
        stats[auth]['ALL win-rate %'] = stats[auth]['wins'] / stats[auth]['matches']
        stats[auth]['ELO_matches'] = len(users[users_invert[auth]]['elo']) - 1
        stats[auth]['ALL matches'] = stats[auth]['matches']


    df = pd.DataFrame(stats).T.sort_values(by=['ELO'], ascending=False, ignore_index=True)
    df = df[['NICK', 'ELO', 'ELO_matches', 'ALL win-rate %', 'ALL matches']]

    results_to_sheet(df[df['ALL matches'] > 4 ])