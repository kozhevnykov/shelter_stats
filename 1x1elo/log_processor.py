import os, re
from datetime import datetime

game_started = re.compile("((?:\d+\.?){3} \d+:\d+:\d+.\d) : Game started.*")
game_stopped = re.compile("((?:\d+\.?){3} \d+:\d+:\d+.\d) : Game stopped.*")
betterlogs = re.compile(
    "(?:\d+\.?){3} \d+:\d+:\d+.\d : 💡 BetterLogs: Joined player.* id: (\d+), name: (.*), ip: \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}, auth: (.+)")
betterlogs_geo = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : 💡 BetterLogs: Player .*")
chatline = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : .*#\d+ : .*")
team_win_match = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : (\w{3,4}) team won the match")
player_side = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : (.*) was moved to (\w{3,4})$")
goal_line = re.compile("(?:\d+\.?){3} \d+:\d+:\d+.\d : 📢 : (.+) Гол для (.*)! \| (.*)")

class LogProcessor:
    def __init__(self, folder='vps-logs--ua-1-1--2/hax/out', first_file_name='out__2024-04-01_23-59-00.log'):
        self.folder = folder
        self.first_file_name = first_file_name

        self.players = {}
        self.match_id = 0
        self.current_match = {'status': '', 'id': -1, 'logs': []}
        self.db_matches = []
        self.stack_players = {}
        self.players = {}

    def run(self):
        for filename in [f for f in sorted(os.listdir(self.folder)) if f >= self.first_file_name] + ['out.log']:
            f = os.path.join(self.folder, filename)
            if filename == '.DS_Store':
                continue
            with open(f, 'r', encoding='utf-8') as file:
                for line in file:
                    self.processing(line)
        print(f'ALL matches - {len(self.db_matches)}, players - {len(self.players)}')

    def processing_nick(self, line):
        if betterlogs.match(line):
            nick = betterlogs.match(line).group(2).strip()
            auth = betterlogs.match(line).group(3)
            if auth not in self.players.keys():
                self.players[auth] = {nick: 1}
            else:
                if nick in self.players[auth].keys():
                    self.players[auth][nick] += 1
                else:
                    self.players[auth][nick] = 1
    @staticmethod
    def starting_lineup( match):
        players = {'Red': [], 'Blue': []}
        for event in match:
            if game_started.match(event):
                break
            if player_side.match(event):
                players[player_side.match(event).group(2)].append(player_side.match(event).group(1).strip())
        return players

    @staticmethod
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

    def processing(self, line):

        if not chatline.match(line) and not betterlogs.match(line) and not betterlogs_geo.match(line):
            self.current_match['logs'].append(line.strip())

        if game_stopped.match(line):
            self.current_match['status'] = 'stopped'
            self.current_match['stopped_at'] = datetime.strptime(game_stopped.match(line).group(1),
                                                            '%d.%m.%Y %H:%M:%S.%f')
            self.analyse_match()

            del (self.current_match['logs'])
            if self.current_match['status'] == 'stopped':
                self.db_matches.append(self.current_match)
            self.match_id += 1
            self.current_match = {'status': 'init', 'id': self.match_id, 'logs': []}
        if game_started.match(line):
            self.current_match['status'] = 'in progress',
            self.current_match['start_at'] = datetime.strptime(game_started.match(line).group(1),
                                                          '%d.%m.%Y %H:%M:%S.%f')

        if betterlogs.match(line):
            self.processing_nick(line)
            nickname = betterlogs.match(line).group(2).strip()
            auth_key = betterlogs.match(line).group(3)
            self.stack_players[nickname] = auth_key

    def analyse_match(self):
        match = self.current_match['logs']
        match_players = self.starting_lineup(match)
        match_winner = self.match_result(match)
        match_stats = self.get_stats(match_winner, match_players)
        self.current_match.update(match_stats)

    def get_stats(self, winner, players):
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
            if k in self.stack_players.keys():
                player_stats_auth[self.stack_players[k].strip()] = v
        return {'stats': player_stats_auth}