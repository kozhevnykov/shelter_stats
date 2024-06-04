import operator
import pandas as pd

class EloStatsCalculator:
    def __init__(self, db_matches, players, min_matches=10):
        self.db_matches = db_matches
        self.players = players
        self.min_matches = min_matches
        self.stats = self.get_stats_from_db_matches()
        self.users, self.users_invert = self.get_users_from_players()
        self.blacklist = {'Vh2iYyJEP3DxxnmDTBwMe1fxbm47EhbttdHEsUVaIOA': 'l1ch'}
        self.df = None
        self.df_elo_matches = None

    def run(self):
        self.update_db_matches_with_stats()
        self.df =  self.update_users_with_stats_df()
        self.df_elo_matches = self.get_df_elo_matches()

    def get_stats_from_db_matches(self):
        stats = {}
        for match in self.db_matches:
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

    def elo_calc(self, match_stats, k=30):
        e1 = self.users[self.users_invert[match_stats[0][0]]]['elo'][-1]
        e2 = self.users[self.users_invert[match_stats[1][0]]]['elo'][-1]

        p1 = 1 / (1 + 10 ** ((e2 - e1) / 400))
        p2 = 1 / (1 + 10 ** ((e1 - e2) / 400))

        ne1 = e1 + k * (match_stats[0][1]['wins'] - p1)
        ne2 = e2 + k * (match_stats[1][1]['wins'] - p2)

        self.users[self.users_invert[match_stats[0][0]]]['elo'].append(round(ne1))
        self.users[self.users_invert[match_stats[1][0]]]['elo'].append(round(ne2))

        # print([e1,e2],[ne1,ne2], p1, p2, {match_stats[0][0], match_stats[1][0]})
    @staticmethod
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

    @staticmethod
    def lose_streak_calc(elos):
        base = 0
        current = 0
        if len(elos) > 1:
            for i in range(len(elos)-1):
                if elos[i] >= elos[i+1]:
                    current += 1
                else:
                    if base < current:
                        base = current
                    current = 0
        return max(base, current)

    @staticmethod
    def n_games_elo_change(elos, n):
        if len(elos) > n:
            return elos[-1] - elos[-n]
        else:
            return None

    @staticmethod
    def biggest_elo_lost_in_single_game(elos):
        if len(elos) > 1:
            return min([elos[i] - elos[i+1] for i in range(len(elos)-1)])
        else:
            return None

    @staticmethod
    def best_elo_rank(elos):
        if len(elos) > 1:
            return max(elos)
        else:
            return None

    def most_played_opponent(self, username):
        print(username, len(self.df_elo_matches))
        df = self.df_elo_matches
        # Filter matches where the user is either player 1 or player 2
        p1_matches = df[df['p1'] == username][['p2', 'p1_elo_diff']]
        p2_matches = df[df['p2'] == username][['p1', 'p2_elo_diff']]

        # Rename columns for uniformity
        p1_matches.columns = ['opponent', 'elo_diff']
        p2_matches.columns = ['opponent', 'elo_diff']

        # Combine the opponents and elo differences into a single DataFrame
        all_matches = pd.concat([p1_matches, p2_matches])

        # Find the most frequent opponent
        if not all_matches.empty:
            most_played = all_matches['opponent'].value_counts().idxmax()
            most_played_count = all_matches['opponent'].value_counts().max()

            # Calculate total Elo gained/lost against this opponent
            elo_gain_loss = all_matches[all_matches['opponent'] == most_played]['elo_diff'].sum()

            return most_played, most_played_count, elo_gain_loss
        else:
            return None, 0, 0


    def get_users_from_players(self):
        users = {}
        for auth, nick_list in dict(sorted(self.players.items(),
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

    def update_db_matches_with_stats(self):
        # calculating elo for each match
        for i in range(len(self.db_matches)):
            m = self.db_matches[i]
            good_match = True
            if len(m['stats'].keys()) != 2:
                good_match = False
            for auth in m['stats'].keys():
                if (auth not in self.users_invert.keys() or self.stats[auth]['matches'] < self.min_matches
                        or auth in self.blacklist.keys()):
                    good_match = False
                # if auth == 'nzaKskHI':
                #     pprint.pprint(m)
            if good_match:
                self.db_matches[i]['status'] = 'ELO stopped'
                for idkey in self.db_matches[i]['stats']:
                    self.db_matches[i]['stats'][idkey]['elo_begin'] = self.users[self.users_invert[idkey]]['elo'][-1]
                self.elo_calc(list(m['stats'].items()))
                for idkey in self.db_matches[i]['stats']:
                    self.db_matches[i]['stats'][idkey]['elo_end'] = self.users[self.users_invert[idkey]]['elo'][-1]
                    self.db_matches[i]['stats'][idkey]['elo_diff'] = (self.db_matches[i]['stats'][idkey]['elo_end'] -
                                                                      self.db_matches[i]['stats'][idkey]['elo_begin'])

    def update_users_with_stats_df(self):
        users = self.users
        for user in users:
            users[user]['NICK'] = user
            users[user]['ELO'] = users[user]['elo'][-1]
            users[user]['matches'] = len(users[user]['elo']) - 1
            users[user]['ALL matches'] = 0
            users[user]['wins'] = 0
            users[user]['win-streak'] = self.win_streak_calc(users[user]['elo'])
            users[user]['lose-streak'] = self.lose_streak_calc(users[user]['elo'])
            users[user]['last10gamesELOchange'] = self.n_games_elo_change(users[user]['elo'], 10)
            users[user]['biggest_elo_lost'] = self.biggest_elo_lost_in_single_game(users[user]['elo'])
            users[user]['highest_elo_rank'] = self.best_elo_rank(users[user]['elo'])
            # (users[user]['most_played_opponent'], users[user]['most_played_opponent_count'],
            #  users[user]['elo_gain_loss']) = self.most_played_opponent(user)

            for idkey in users[user]['idkeys']:
                if idkey in self.stats.keys():
                    users[user]['ALL matches'] += self.stats[idkey]['matches']
                    users[user]['wins'] += self.stats[idkey]['wins']
            if users[user]['ALL matches'] > 0:
                users[user]['WR %'] = users[user]['wins'] / users[user]['ALL matches']
            else:
                users[user]['WR %'] = None

        self.users = users
        df = pd.DataFrame(users).T.sort_values(by=['ELO'], ascending=False)
        df = df[['NICK', 'ELO', 'matches', 'WR %', 'win-streak', 'lose-streak', 'last10gamesELOchange',
                 'biggest_elo_lost', 'highest_elo_rank']]

        return df[df['matches'] >= self.min_matches]

    def get_df_elo_matches(self):
        df_elo_matches = pd.DataFrame({'id': [], 'started_at': [],
                                       'p1': [], 'p1_elo_begin': [], 'p1_elo_diff': [],
                                       'p2': [], 'p2_elo_begin': [], 'p2_elo_diff': []})
        for m in self.db_matches:
            if m['status'] == 'ELO stopped':
                df_elo_matches.loc[len(df_elo_matches)] = [m['id'], m['start_at'].strftime('%d.%m.%Y %H'),
                                                           self.users[self.users_invert[list(m['stats'].keys())[0]]]['NICK'],
                                                           m['stats'][list(m['stats'].keys())[0]]['elo_begin'],
                                                           m['stats'][list(m['stats'].keys())[0]]['elo_diff'],
                                                           self.users[self.users_invert[list(m['stats'].keys())[1]]]['NICK'],
                                                           m['stats'][list(m['stats'].keys())[1]]['elo_begin'],
                                                           m['stats'][list(m['stats'].keys())[1]]['elo_diff']]

        df_elo_matches = df_elo_matches.sort_values(by=['id'], ignore_index=True, ascending=False)

        return df_elo_matches