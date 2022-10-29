from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguestandingsv3, boxscoresummaryv2

import requests
import json
import pandas as pd
from datetime import datetime

PRESEASON_DATE = "2022-10-17"
T = datetime.now()

def get_team_id(team_name: str) -> int:
    nba_teams = teams.get_teams()
    id = 0

    # t is a dictionary with the keys: 
    # id, full_name, abbreviation, nickname, city, state, and year founded
    for t in nba_teams:
        if t["full_name"] == team_name:
            id = t["id"]
    
    return id


def get_league_standings() -> pd.DataFrame:
    standings = leaguestandingsv3.LeagueStandingsV3().standings.get_data_frame()
    small_standings = standings[["TeamName", "Conference", "Record"]].copy()
    small_standings.sort_values(by=["Conference", "Record"], ascending=False,  inplace=True)
    small_standings = small_standings.reset_index(drop=True)

    # blank row to divide conferences
    small_standings.loc[14.5] = "", "", ""

    # re-sort index
    small_standings = small_standings.sort_index().reset_index(drop=True)

    return small_standings


def get_last_game_score(games: pd.DataFrame) -> pd.DataFrame:
    prev_games = games.loc[(games["gameDateTimeEst"] < T)]
    last_game = prev_games.iloc[-1]
    last_game_id = last_game["gameId"]

    scores = boxscoresummaryv2.BoxScoreSummaryV2(last_game_id).line_score.get_data_frame()
    scores = scores[["TEAM_ABBREVIATION", "PTS"]]
    
    return scores


def get_next_game(games: pd.DataFrame) -> pd.Series:
    future_games = games.loc[(games["gameDateTimeEst"] > T)]
    next_game = future_games.iloc[0]
    
    # convert to dataframe
    next_game = pd.DataFrame(next_game)
    next_game = next_game.transpose()
    next_game = next_game[["gameDateTimeEst", "awayTeam", "homeTeam", "channel"]]

    # split datetime into separate columns
    next_game["gameDateTimeEst"] = pd.to_datetime(next_game["gameDateTimeEst"])
    next_game["Date"] = next_game["gameDateTimeEst"].dt.date
    next_game["Time"] = next_game["gameDateTimeEst"].dt.time

    # drop datetime column and convert to series
    next_game = next_game.drop(columns="gameDateTimeEst")
    next_game = next_game.iloc[0]

    return next_game


def get_team_schedule(team_id: int) -> pd.DataFrame:
    #headers
    headers = {
        'Host': 'cdn.nba.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'x-nba-stats-origin': 'stats',
        'x-nba-stats-token': 'true',
        'Connection': 'keep-alive',
        'Origin': 'https://cdn.nba.com',
        'Referer': 'https://cdn.nba.com',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache'
    }

    #get games from schedule
    url = 'https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json'
    r = requests.get(url, headers=headers)
    schedule = r.json()
    schedule = schedule['leagueSchedule']['gameDates']

    # Write pretty print JSON data to file
    # with open("schedule.json", "w") as f:
    #     json.dump(schedule, f, indent=4)

    games = []
    for l in schedule:
        game = l['games']
        
        for l in game:

            # check for national broadcast
            if len(l["broadcasters"]["nationalBroadcasters"]):
                channel = l["broadcasters"]["nationalBroadcasters"][0]["broadcasterDisplay"]
            else:
                channel = "League Pass"

            g = [l['gameId'],l['gameDateTimeEst'],l['awayTeam']['teamName'],l['homeTeam']['teamName'], channel, l["homeTeam"]["teamId"], l["awayTeam"]["teamId"] ]

            df = pd.DataFrame([g], columns =['gameId','gameDateTimeEst','awayTeam','homeTeam','channel', 'homeTeamID', 'awayTeamID'])
            games.append(df)

    games = pd.concat(games)

    # localize times
    games['gameDateTimeEst'] = pd.to_datetime(games['gameDateTimeEst'], format="%Y-%m-%dT%H:%M:%S.%f", errors = 'coerce').dt.tz_localize(None)

    # get games of team
    team_games = games.loc[((games['awayTeamID'] == team_id) | (games['homeTeamID'] == team_id)) & (games['gameDateTimeEst'] >= PRESEASON_DATE)]

    return team_games