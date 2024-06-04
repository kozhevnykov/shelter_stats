import log_processor, elo_stats, publisher

if __name__ == '__main__':

    parsed_logs = log_processor.LogProcessor(
        folder='../vps-logs--ua-1-1--2/hax/out',
        first_file_name='out__2024-04-01_23-59-00.log'
    )
    parsed_logs.run()

    calculated_elo = elo_stats.EloStatsCalculator(
        db_matches=parsed_logs.db_matches,
        players=parsed_logs.players,
        min_matches=10
    )
    calculated_elo.run()

    publisher.results_to_sheet(calculated_elo.df, worksheet=1)
    publisher.results_to_sheet(calculated_elo.df_elo_matches, worksheet=2)

    calculated_elo.df.to_csv('df.csv', index=False)
    calculated_elo.df_elo_matches.to_csv('df_elo_matches.csv', index=False)
