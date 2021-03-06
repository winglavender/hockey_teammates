import pandas as pd
import sqlite3 as sql
import unicodedata
import time
import re
import matplotlib as mpl
from matplotlib.afm import AFM
import os.path

class hockey_db():

    def __init__(self):
        db_name = 'hockey_rosters_20220718_formatted.db'
        conn = sql.connect(db_name)
        self.skaters = pd.read_sql_query('select * from skaters', conn)
        self.postseasons = pd.read_sql_query('select * from postseasons', conn)
        self.skaters.start_date = pd.to_datetime(self.skaters.start_date)
        self.skaters.end_date = pd.to_datetime(self.skaters.end_date)
        self.names = pd.read_sql_query('select * from names', conn)
        self.league_strings = {'nhl': 'NHL', 'og': 'Olympics', 'khl': 'KHL', 'ahl': 'AHL', 'wc': 'Worlds', 'ohl': 'OHL', 'whl': 'WHL', 'qmjhl': 'QMJHL', 'ushl': 'USHL', 'usdp': 'USDP', 'ncaa': 'NCAA', 'wjc-20': 'World Juniors', 'wjc-18': 'WC-U18', 'whc-17': 'WHC-17', 'wcup': 'World Cup', 'shl': 'SHL', 'mhl': 'MHL', 'liiga': 'Liiga', 'u20-sm-liiga': 'U20 SM Liiga', 'u18-sm-sarja': 'U18 SM Sarja', 'j20-superelit': 'J20 SuperElit', 'j18-allsvenskan': 'J18 Allsvenskan', 'russia': 'Russia', 'russia3': 'Russia3', 'ushs-prep': 'USHS Prep'}
        #self.tournament_leagues = set(['og', 'wc', 'wjc-20', 'wjc-18', 'whc-17', 'wcup'])
        self.tournament_leagues = {'og': (2,1), 'wjc-20': (1,1), 'wc': (6,1), 'wjc-18': (4,1), 'whc-17': (11,0), 'wcup': (9,0)} # first value is month and second value is 0 if the first year in a season should be used, 1 if the second year in the season should be used
        # for font-accurate string comparisons
        afm_filename = os.path.join(mpl.get_data_path(), 'fonts', 'afm', 'ptmr8a.afm')
        self.afm = AFM(open(afm_filename, "rb"))

    def get_string_width(self, input_string):
        width, height = self.afm.string_width_height(input_string)
        return width

    def categorize_league_list(self, league_list):
        contains_nhl = False
        contains_non_national = False
        national_set = set(['World Juniors','Worlds','Olympics','WC-U18','WHC-17','World Cup'])
        for league in league_list:
            if league == 'NHL':
                return 'blue' # NHL
            elif league not in national_set:
                contains_non_national = True
        if contains_non_national:
            return 'green' # other
        else:
            return 'red' # national teams only

    def get_league_display_string(self, league_str):
        if league_str not in self.league_strings:
            return league_str
        return self.league_strings[league_str]

    def get_team_display_string(self, league_str, team_str):
        if league_str == 'og':
            return f"{team_str} Olympics"
        elif league_str == 'wc':
            return f"{team_str} Worlds"
        elif league_str == 'wcup':
            return f"{team_str} World Cup"
        elif league_str == 'wjc-20':
            return f"{team_str} World Juniors"
        elif league_str == 'wjc-18':
            return f"{team_str} Worlds"
        elif league_str == 'whc-17':
            return f"{team_str}"
        else:
            return team_str

    def is_tournament(self, league_str):
        if league_str in self.tournament_leagues:
            return True
        return False

    def convert_tournament_dates(self, tournament, start_date, end_date):
        season_years = (start_date.year, end_date.year)
        tourney_month, tourney_year = self.tournament_leagues[tournament]
        return (pd.to_datetime(f"{season_years[tourney_year]}/{tourney_month}/1"), pd.to_datetime(f"{season_years[tourney_year]}/{tourney_month}/28"))
        #start_year = start_date.year
        #end_year = end_date.year
        #return (pd.to_datetime(f"{start_year}/12/15"), pd.to_datetime(f"{end_year}/1/15"))

    def compute_overlap_interval(self, start_date1, end_date1, start_date2, end_date2):
        start_dates = pd.DataFrame([pd.to_datetime(start_date1), pd.to_datetime(start_date2)])
        end_dates = pd.DataFrame([pd.to_datetime(end_date1), pd.to_datetime(end_date2)])
        start_interval = start_dates.max().iloc[0]
        end_interval = end_dates.min().iloc[0]
        num_seasons = max(1, end_interval.year-start_interval.year)
        if start_interval <= end_interval:
            return (start_interval, end_interval), num_seasons
        else:
            return False, 0

    def get_terms_from_player_id(self, player_id):
        return self.skaters.loc[self.skaters.link==player_id]

    def get_player_career(self, player_id):
        output = []
        player_rows = self.get_terms_from_player_id(player_id)
        playername = self.get_player_name_from_id(player_id)
        playoff_queries = []
        for index, term in player_rows.iterrows():
            team_display_str = self.get_team_display_string(term.league, term.team)
            tooltip_str = f"{team_display_str}<br>{term.start_date.year}-{term.end_date.year}"
            if self.is_tournament(term.league):
                term_dates = self.convert_tournament_dates(term.league, term.start_date, term.end_date)
                team_display_str = ""
                color = "80b4f2"#"a994ff"#"f74d4d"#"faa7a7"#"#a7d5fa"
            else:
                term_dates = (term.start_date, term.end_date)
                color = "2e7cdb"#"348cf7"#"247abf"#"#20a840"
            output.append({"player": playername, "league": term.league, "team_display": team_display_str, "year1": term_dates[0].year, "month1": term_dates[0].month, "day1": term_dates[0].day, "year2": term_dates[1].year, "month2": term_dates[1].month, "day2": term_dates[1].day, "tooltip_str": tooltip_str, "id": player_id, "color": color}) 
            # check for playoff query
            if term.league == "nhl":
                if term.start_date <= pd.to_datetime(f"{term.start_date.year}/4/30") and term.end_date >= pd.to_datetime(f"{term.end_date.year}/6/30"):
                    playoff_queries.append((term.team, f"{term.start_date.year-1}-{term.start_date.year}"))
                if term.start_date.year != term.end_date.year:
                    for i in range(term.start_date.year, term.end_date.year-1):
                        playoff_queries.append((term.team, f"{i}-{i+1}"))
                    if term.end_date >= pd.to_datetime(f"{term.end_date.year}/6/30"):
                        playoff_queries.append((term.team, f"{term.end_date.year-1}-{term.end_date.year}"))
        # get playoff runs
        for team, playoff_year in playoff_queries:
            team_str = self.strip_accents(team)
            year = playoff_year.split("-")[1]
            result = self.postseasons.loc[(self.postseasons.Team==team_str) & (self.postseasons.Season==playoff_year)].Postseason
            result = self.postseasons.loc[(self.postseasons.Team==team_str) & (self.postseasons.Season==playoff_year)].Postseason.item()
            tooltip_str = f"{playoff_year}<br>{result}"
            if result == "Did not make playoffs":
                color = "#cfcecc"
            elif result == "Champion":
                color = "fae525"#"f0ea3e"#"fff945"#"#f5d236"
            else:
                color = "ebb11e"#fcbe03"
            output.append({"player": "", "league": "nhl", "team_display": "", "year1": year, "month1": 5, "day1": 1, "year2": year, "month2": 5, "day2": 30, "tooltip_str": tooltip_str, "id": player_id, "color": color})
        return output

    def get_overlapping_player_terms(self, player1_id, player2_id=None):
        output = []
        player_rows = self.get_terms_from_player_id(player1_id)
        for index, term in player_rows.iterrows():
            if player2_id: # only return overlaps involving this specific second target player
                overlaps_a = self.skaters.loc[(self.skaters.league==term.league) & (self.skaters.team==term.team) & (self.skaters.link==player2_id) & (self.skaters.start_date>=term.start_date) & (self.skaters.start_date<term.end_date)]
                overlaps_b = self.skaters.loc[(self.skaters.league==term.league) & (self.skaters.team==term.team) & (self.skaters.link==player2_id) & (term.start_date>self.skaters.start_date) & (term.start_date<self.skaters.end_date)]
            else: # return overlaps involving any other player
                overlaps_a = self.skaters.loc[(self.skaters.link!=player1_id) & (self.skaters.league==term.league) & (self.skaters.team==term.team) & (self.skaters.start_date>=term.start_date) & (self.skaters.start_date<term.end_date)]
                overlaps_b = self.skaters.loc[(self.skaters.link!=player1_id) & (self.skaters.league==term.league) & (self.skaters.team==term.team) & (term.start_date>self.skaters.start_date) & (term.start_date<self.skaters.end_date)]
            overlaps = pd.concat([overlaps_a, overlaps_b])
            team_display_str = self.get_team_display_string(term.league, term.team)
            for teammate_id in overlaps.link.unique():
                teammate_rows = overlaps.loc[overlaps.link==teammate_id] # get all overlapping terms for this teammate (same as overlaps if player2_id was specified)
                for index, teammate_term in teammate_rows.iterrows():
                    overlap_term, season_count = self.compute_overlap_interval(term.start_date, term.end_date, teammate_term.start_date, teammate_term.end_date)
                    tooltip_str = f"{teammate_term.player}<br>{team_display_str}<br>{overlap_term[0].year}-{overlap_term[1].year}"
                    if self.is_tournament(term.league):
                        overlap_term = self.convert_tournament_dates(term.league, overlap_term[0], overlap_term[1])
                    else:
                        if season_count == 1:
                            tooltip_str += f" ({season_count} season)"
                        else:
                            tooltip_str += f" ({season_count} seasons)"
                    output.append((overlap_term[0].year, overlap_term[0].month, overlap_term[0].day, [teammate_rows.iloc[0].player, term.league, term.team, team_display_str, overlap_term[0].year, overlap_term[0].month, overlap_term[0].day, overlap_term[1].year, overlap_term[1].month, overlap_term[1].day, tooltip_str, teammate_rows.iloc[0].link]))
        # sort all overlaps by first overlap year
        output.sort()
        sorted_output = []
        longest_name = ""
        for year, month, day, data in output:
            sorted_output.append({"player": data[0], "league": self.get_league_display_string(data[1]), "team": data[2], "team_display": data[3], "year1": data[4], "month1": data[5], "day1": data[6], "year2": data[7], "month2": data[8], "day2": data[9], "tooltip_str": data[10], "id": data[11]})
            if self.get_string_width(self.strip_accents(data[0])) > self.get_string_width(self.strip_accents(longest_name)):
                longest_name = data[0]
        return sorted_output, longest_name

    def get_players_from_roster(self, team, season):
        # set up season start/end timestamps
        years = season.split("-")
        season_start = pd.to_datetime(f"{years[0]}/9/1")
        season_end = pd.to_datetime(f"{years[1]}/6/30")
        # get players
        teammates_a = self.skaters.loc[(self.skaters.league=="nhl") & (self.skaters.team==team) & (self.skaters.start_date >= season_start) & (self.skaters.start_date<season_end)]
        teammates_b = self.skaters.loc[(self.skaters.league=="nhl") & (self.skaters.team==team) & (season_start>self.skaters.start_date) & (season_start<self.skaters.end_date)]
        potential_teammates = pd.concat([teammates_a,teammates_b])
        return potential_teammates

    def query_roster_pair(self, team1, team2, season):
        start = time.time()
        # get players from team1
        players1 = self.get_players_from_roster(team1, season)
        ids1 = players1.link.unique()
        # get players from team2
        players2 = self.get_players_from_roster(team2, season)
        ids2 = players2.link.unique()
        # all pairs of players, get names
        team1_players_list = []
        player_id_to_name = {}
        for player1 in ids1:
            playername = self.get_player_name_from_id(player1)
            team1_players_list.append(playername)
            player_id_to_name[player1] = playername
        team2_players_list = []
        for player2 in ids2:
            playername = self.get_player_name_from_id(player2)
            team2_players_list.append(playername)
            player_id_to_name[player2] = playername
        # even out length
        if len(team1_players_list) < len(team2_players_list):
            while len(team1_players_list) < len(team2_players_list):
                team1_players_list.append("zzzplaceholder")
        if len(team2_players_list) < len(team1_players_list):
            while len(team2_players_list) < len(team1_players_list):
                team2_players_list.append("zzzplaceholder")
        # alphabetize
        team1_players_list.sort(reverse=True)
        team1_players_index = {}
        for idx, playername in enumerate(team1_players_list):
            team1_players_index[playername] = idx
        team2_players_list.sort(reverse=True)
        team2_players_index = {}
        for idx, playername in enumerate(team2_players_list):
            team2_players_index[playername] = idx
        # turn placeholder strings into empty strings (now that indices are set)
        for idx, playername in enumerate(team1_players_list):
            if playername == "zzzplaceholder":
                team1_players_list[idx] = ""
        for idx, playername in enumerate(team2_players_list):
            if playername == "zzzplaceholder":
                team2_players_list[idx] = ""
        # find links
        connections = []
        for player1 in ids1:
            playername1 = player_id_to_name[player1]
            player_data = {} 
            potential_overlap, _ = self.get_overlapping_player_terms(player1)
            for row in potential_overlap:
                if row['id'] in ids2:
                    playername2 = player_id_to_name[row['id']]
                    relationships = self.is_before_after_during_season(season, row['year1'], row['month1'], row['day1'], row['year2'], row['month2'], row['day2'])
                    if 'before' not in relationships and 'during' not in relationships:
                        continue # ignore terms that only occur AFTER the current season
                    data = f"{row['team']} ({row['league']}, {row['year1']}-{row['year2']})"
                    if playername2 not in player_data:
                        player_data[playername2] = []
                    player_data[playername2].append((data, row['league']))
            output_tmp = []
            for playername2 in player_data:
                # create a link
                data_strs = []
                data_leagues = []
                for data_str, league in player_data[playername2]:
                    data_strs.append(data_str)
                    data_leagues.append(league)
                idx1 = team1_players_index[playername1]
                idx2 = team2_players_index[playername2]
                relationship_type = self.categorize_league_list(data_leagues)
                link_str = ", ".join(data_strs)
                out_str = f"{playername1} ({link_str})--{playername2} ({link_str})" 
                connections.append((idx1, idx2, out_str, relationship_type))
        # format output
        output = {'team1_players': team1_players_list, 'team2_players': team2_players_list, 'links': connections}
        end = time.time()
        print(f"elapsed time: {end-start}")
        return output
            
    
    def query_roster(self, player_id, team, season):
        start = time.time()
        output = []
        # set up season start/end timestamps
        #years = season.split("-")
        #season_start = pd.to_datetime(f"{years[0]}/9/1")
        #season_end = pd.to_datetime(f"{years[1]}/6/30")
        # get all players from (team, year) roster
        potential_teammates = self.get_players_from_roster(team, season)
        #teammates_a = self.skaters.loc[(self.skaters.league=="nhl") & (self.skaters.team==team) & (self.skaters.link!=player_id) & (self.skaters.start_date >= season_start) & (self.skaters.start_date<season_end)]
        #teammates_b = self.skaters.loc[(self.skaters.league=="nhl") & (self.skaters.team==team) & (self.skaters.link!=player_id) & (season_start>self.skaters.start_date) & (season_start<self.skaters.end_date)]
        #potential_teammates = pd.concat([teammates_a,teammates_b])
        potential_teammate_ids = potential_teammates.link.unique()
        output = {"before": [], "during": [], "after": []}
        # get all teammates for target player
        all_player_teammates, _ = self.get_overlapping_player_terms(player_id)
        # reformat
        overlapping_teammates = {}
        for row in all_player_teammates:
            if row['id'] in potential_teammate_ids:
                if row['id'] not in overlapping_teammates:
                    overlapping_teammates[row['id']] = []
                overlapping_teammates[row['id']].append(row)
        for teammate_id in overlapping_teammates:
            overlap = overlapping_teammates[teammate_id]
            if len(overlap) > 0:
                playername = self.get_player_name_from_id(teammate_id)
                formatted_data = {"before": [], "after": [], "during": []}
                for term in overlap:
                    relationships = self.is_before_after_during_season(season, term['year1'], term['month1'], term['day1'], term['year2'], term['month2'], term['day2'])
                    for relationship in relationships:
                        formatted_data[relationship].append(f"{term['team']} ({term['league']}, {term['year1']}-{term['year2']})")
                for relationship in formatted_data:
                    if len(formatted_data[relationship]) > 0:
                        player_data = {"playername": playername, "data": ", ".join(formatted_data[relationship])}
                        output[relationship].append((playername, player_data))
        #output.sort()
        sorted_output = {"before": [], "after": [], "during": []}
        for relationship in output:
            output[relationship].sort()
            for name, data in output[relationship]:
                sorted_output[relationship].append(data)
        end = time.time()
        print(f"elapsed time: {end-start}")
        return sorted_output, len(sorted_output["before"]) + len(sorted_output["after"]) + len(sorted_output["during"])

    # returns list of terms to specify whether the period START_YEAR to END_YEAR happens BEFORE/DURING/AFTER the specified season
    def is_before_after_during_season(self, season, year1, month1, day1, year2, month2, day2):
        start_date = pd.to_datetime(f"{year1}/{month1}/{day1}")
        end_date = pd.to_datetime(f"{year2}/{month2}/{day2}")
        season_years = season.split("-")
        season_start_year = int(season_years[0])
        season_end_year = int(season_years[1])
        season_start = pd.to_datetime(f"{season_start_year}/9/1")
        season_end = pd.to_datetime(f"{season_end_year}/6/30")
        last_season_end = pd.to_datetime(f"{season_start_year}/6/30")
        next_season_start = pd.to_datetime(f"{season_end_year}/9/1")
        relationship = []
        if start_date < last_season_end:
            relationship.append("before")
        if end_date > next_season_start: 
            relationship.append("after")
        if start_date <= season_start and end_date >= season_start:
            relationship.append("during")
        if start_date <= season_end and end_date >= season_end:
            relationship.append("during")
        return relationship

    def get_player_name_from_id(self, player_id):
        terms = self.get_terms_from_player_id(player_id)
        return terms.iloc[0].player # player_id is unique, it doesn't matter which row we use for the name

    def player_to_description(self, player_row):
        year1 = pd.to_datetime(player_row.start_date).year
        year2 = pd.to_datetime(player_row.end_date).year
        return f"most recently {player_row.team} ({year1}-{year2})"

    # for all multiple possible players for a given name input, 
    # list out all options, each with an attached description of the most recent NHL team they played for 
    def format_multiple_options(self, links):
        unique_players = {}
        for index, row in links.iterrows():
            if row.link not in unique_players:
                unique_players[row.link] = {'player': row.player, 'link': row.link, 'start_date': row.start_date, 'end_date': row.end_date, 'description': self.player_to_description(row), 'team': row.team}
            else:
                other_start_date = unique_players[row.link]['start_date']
                if row.start_date > other_start_date and row.league == 'nhl':
                    # new latest season (restrict to NHL only), update player info
                    unique_players[row.link] = {'player': row.player, 'link': row.link, 'start_date': row.start_date, 'end_date': row.end_date, 'description': self.player_to_description(row), 'team': row.team}
        return unique_players.values()

    def strip_accents(self, text):
        try:
            text = unicode(text, 'utf-8')
        except NameError: # unicode is a default on python 3
            pass
        text = unicodedata.normalize('NFD', text)\
               .encode('ascii', 'ignore')\
               .decode("utf-8")
        text = text.replace("-"," ") # handle hyphenated names
        text = re.sub(r'[^\w\s]', '', text) # remove punctuation (e.g. "J.T. Brown")
        return str(text)


    # given an input name, return the player id (EliteProspects url)
    # if there are multiple possible players, return all possibilities, each with a description
    def retrieve_player_link(self, name):
        tgt_name = self.strip_accents(name.lower())
        names = self.names.loc[self.names.norm_name==tgt_name]
        unique_ids = set()
        for index, name_row in names.iterrows():
            ids = self.skaters.loc[self.skaters.player==name_row.orig_name]
            unique_ids.update(list(ids.link.unique()))
        if len(unique_ids) == 1:
            return 1, (names.iloc[0].orig_name, list(unique_ids)[0])
        elif len(unique_ids) == 0:
            return 0, name
        else:
            # format output
            output = self.format_multiple_options(ids)
            return len(output), output

    def traverse_graph(self, player1_id, player2_id):
        teammates1, _ = self.get_overlapping_player_terms(player1_id)
        teammates1_dict = {}
        for row in teammates1:
            if row['id'] not in teammates1_dict:
                teammates1_dict[row['id']] = []
            teammates1_dict[row['id']].append(row)
        teammates2, _ = self.get_overlapping_player_terms(player2_id)
        overlapping_teammates = {}
        for row in teammates2:
            if row['id'] in teammates1_dict:
                if row['id'] not in overlapping_teammates:
                    overlapping_teammates[row['id']] = []
                overlapping_teammates[row['id']].append(row)
        # format results
        output = []
        for player_id in overlapping_teammates:
            player_name = self.get_player_name_from_id(player_id)
            output.append((player_name, self.condense_terms_into_table_rows(teammates1_dict[player_id], overlapping_teammates[player_id])))
        output.sort()
        sorted_output = []
        for player_name, data in output:
            for row in data:
                sorted_output.append(row)
        return sorted_output

    def condense_terms_into_table_rows(self, rows1, rows2):
        player = rows1[0]["player"]
        out_list = []
        max_rows = max(len(rows1), len(rows2))
        cells = []
        for i in range(max_rows):
            row = []
            if i == 0:
                row.append(player)
            else:
                row.append("")
            if i < len(rows1):
                row.append(f'{rows1[i]["team"]} ({rows1[i]["league"]}, {rows1[i]["year1"]}-{rows1[i]["year2"]})')
            else:
                row.append('')
            if i < len(rows2):
                row.append(f'{rows2[i]["team"]} ({rows2[i]["league"]}, {rows2[i]["year1"]}-{rows2[i]["year2"]})')
            else:
                row.append('')
            cells.append(row)
        return cells
