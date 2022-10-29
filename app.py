
import utils

team_id = utils.get_team_id("Golden State Warriors")
standings = utils.get_league_standings()
games = utils.get_team_schedule(team_id)
next_game = utils.get_next_game(games)
scores = utils.get_last_game_score(games)

print()
print(standings.to_string(index=False))
print()
print(scores.to_string(index=False))
print()
print(next_game.to_string())