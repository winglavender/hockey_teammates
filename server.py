from flask import Flask, render_template, request, session
from query_db import hockey_db 
import os

app = Flask(__name__)
if os.getenv('PYANYWHERE'):
    local = False
else:
    local = True
if local:
    app.config.from_pyfile('config.py')
else:
    app.config.update(SECRET_KEY = os.getenv("SECRET_KEY"))

# populate NHL team data
nhl_team_data = {'team_order': [], 'team_seasons': {}}
with open('nhl_team_data.txt','r') as in_file:
    for line in in_file:
        tokens = line.strip().split(",")
        start_year = int(tokens[1])
        end_year = int(tokens[2])
        seasons = []
        for i in range(end_year,start_year,-1):
            seasons.append(f"{i-1}-{i}")
        nhl_team_data['team_order'].append(tokens[0])
        nhl_team_data['team_seasons'][tokens[0]] = seasons
nhl_team_data['team_order'].sort()
nhl_team_data['team1_seasons'] = nhl_team_data['team_seasons'][nhl_team_data['team_order'][0]]

@app.route("/")
def home():
    session.clear()
    return render_template("index.html",nhl_team_data=nhl_team_data)

@app.route("/form_result", methods=["GET","POST"])
def form_result():
    if request.method == "POST":
        session.clear()
        target = request.form['target'].strip()
        db = hockey_db()
        num_results, output = db.retrieve_player_link(target)
        session["task"] = "career"
        session["player2"] = ""
        session["player2_id"] = ""
        if num_results == 1:
            # output is unique player link
            orig_name, player_id = output
            data = db.get_overlapping_player_terms(player_id)
            return render_template('career_results.html', data=data, player=orig_name)
        elif num_results == 0:
            # output is player name searched
            return render_template('no_results.html', playername=output)
        else:
            # output contains list of options for player
            return render_template('options_1.html', data=output)
    else:
        return render_template('error.html')

@app.route("/pair_form_result", methods=["GET","POST"])
def pair_form_result():
    if request.method == "POST":
        session.clear()
        db = hockey_db()
        player1 = request.form['player1'].strip()
        num_results1, target1 = db.retrieve_player_link(player1)
        player2 = request.form['player2'].strip()
        num_results2, target2 = db.retrieve_player_link(player2)
        session["task"] = "pair"
        if num_results1 == 1 and num_results2 == 1:
            # we have unique player ids for both
            orig_name1, player_id1 = target1
            orig_name2, player_id2 = target2
            if player_id1 == player_id2:
                return render_template('pair_same_player.html')
            data = db.get_overlapping_player_terms(player_id1, player_id2)
            if len(data) == 0:
                return render_template('no_pair_results.html', playername1=orig_name1, playername2=orig_name2)
            else:
                return render_template('pair_results.html', data=data, playername1=orig_name1, playername2=orig_name2)
        elif num_results1 == 0:
            return render_template('no_results.html', playername=target1)
        elif num_results2 == 0:
            return render_template('no_results.html', playername=target2)
        elif num_results1 > 1 and num_results2 == 1:
            # clarify player 1
            session["player2"], session["player2_id"] = target2
            session.pop("player1", None)
            session.pop("player1_id", None)
            return render_template('options_1.html', data=target1)
        elif num_results2 > 1 and num_results1 == 1:
            # clarify player 2
            session["player1"], session["player1_id"] = target1
            session.pop("player2", None)
            session.pop("player2_id", None)
            return render_template('options_1.html', data=target2)
        else:
            # clarify both players
            return render_template('options_2.html', data1=target1, data2=target2)
    else:
        return render_template('error.html')

@app.route("/player_team_year_result", methods=["GET", "POST"])
def player_team_year_result():
    if request.method == "POST":
        session.clear()
        player = request.form['player'].strip()
        team = request.form['team']
        season = request.form['season']
        db = hockey_db()
        session["task"] = "roster"
        session["team"] = team
        session["season"] = season
        session["player2"] = ""
        session["player2_id"] = ""
        num_results, target = db.retrieve_player_link(player)
        if num_results == 1:
            # we have a unique player id
            orig_name, player_id = target
            #data = query_player_team_year(player_id, team, season)
            data, len_data = db.query_roster(player_id, team, season)
            if len_data == 0:
                return render_template('no_roster_results.html', playername=orig_name,team=team, season=season)
            else:
                return render_template('roster_results.html', playername=orig_name, team=team, season=season, data=data)
        elif num_results == 0:
            return render_template('no_results.html', playername=target)
        elif num_results > 1:
            # clarify player id
            return render_template('options_1.html', data=target)
    else:
        return render_template('error.html')

@app.route("/graph_traverse_result", methods=["GET", "POST"])
def graph_traverse_result():
    if request.method == "POST":
        session.clear()
        db = hockey_db()
        player1 = request.form['player1'].strip()
        num_results1, target1 = db.retrieve_player_link(player1)
        player2 = request.form['player2'].strip()
        num_results2, target2 = db.retrieve_player_link(player2)
        session["task"] = "traverse"
        if num_results1 == 1 and num_results2 == 1:
            # we have unique player ids for both
            orig_name1, player_id1 = target1
            orig_name2, player_id2 = target2
            if player_id1 == player_id2:
                return render_template('traverse_same_player.html')
            data = db.traverse_graph(player_id1, player_id2)
            if len(data) == 0:
                return render_template('no_traverse_results.html', playername1=orig_name1, playername2=orig_name2)
            else:
                return render_template('traverse_results.html', data=data, playername1=orig_name1, playername2=orig_name2)
        elif num_results1 == 0:
            return render_template('no_results.html', playername=target1)
        elif num_results2 == 0:
            return render_template('no_results.html', playername=target2)
        elif num_results1 > 1 and num_results2 == 1:
            # clarify player 1
            session["player2"], session["player2_id"] = target2
            session.pop("player1", None)
            session.pop("player1_id", None)
            return render_template('options_1.html', data=target1)
        elif num_results2 > 1 and num_results1 == 1:
            # clarify player 2
            session["player1"], session["player1_id"] = target1
            session.pop("player2", None)
            session.pop("player2_id", None)
            return render_template('options_1.html', data=target2)
        else:
            # clarify both players
            return render_template('options_2.html', data1=target1, data2=target2)
    else:
        return render_template('error.html')

@app.route("/options_result_1", methods=["GET", "POST"])
def options_result_1():
    if request.method == "POST":
        print(session)
        target = request.form['playerid']
        tmp = target.split("#")
        if "player1_id" not in session:
            session["player1"] = tmp[0]
            session["player1_id"] = tmp[1] 
        elif "player2_id" not in session:
            session["player2"] = tmp[0]
            session["player2_id"] = tmp[1]
        if session["player1_id"] == session["player2_id"]:
            return render_template(f"{session['task']}_same_player.html")
        db = hockey_db()
        data = []
        if session["task"] == "career":
            data = db.get_overlapping_player_terms(session["player1_id"])
            session["player2"] = "" # dummy
        elif session["task"] == "traverse":
            data = db.traverse_graph(session["player1_id"], session["player2_id"])
            len_data = len(data)
        elif session["task"] == "pair":
            data = db.get_overlapping_player_terms(session["player1_id"], session["player2_id"])
            len_data = len(data)
        elif session["task"] == "roster":
            data, len_data = db.query_roster(session["player1_id"], session["team"], session["season"])
        if len_data == 0 and session["task"] != "career":
            if session["task"] == "roster":
                return render_template('no_roster_results.html', playername=session.get("player1"),team=session.get("team"), season=session.get("season"))
            else:
                return render_template(f'no_{session["task"]}_results.html', playername1=session.get("player1"), playername2=session.get("player2"))
        else:
            if session["task"] == "roster":
                return render_template('roster_results.html', playername=session.get("player1"), team=session.get("team"), season=session.get("season"), data=data)
            else:
                return render_template(f'{session["task"]}_results.html', data=data, playername1=session.get("player1"), playername2=session.get("player2"))
    else:
        return render_template('error.html')

@app.route("/options_result_2", methods=["GET", "POST"])
def options_result_2():
    if request.method == "POST":
        tmp1 = request.form['playerid1'].split("#")
        tmp2 = request.form['playerid2'].split("#")
        session["player1"] = tmp1[0]
        session["player1_id"] = tmp1[1]
        session["player2"] = tmp2[0]
        session["player2_id"] = tmp2[1]
        if session["player1_id"] == session["player2_id"]:
            return render_template(f"{session['task']}_same_player.html")
        db = hockey_db()
        data = []
        if session["task"] == "traverse":
            data = db.traverse_graph(session["player1_id"], session["player2_id"])
        elif session["task"] == "pair":
            data = db.get_overlapping_player_terms(session["player1_id"], session["player2_id"])
        if len(data) == 0:
            return render_template(f'no_{session["task"]}_results.html', playername1=session.get("player1"), playername2=session.get("player2"))
        else:
            return render_template('{session["task"]}_results.html', data=data, playername1=session.get("player1"), playername2=session.get("player2"))
    else:
        return render_template('error.html')

@app.route("/details")
def details():
    return render_template("details.html")

@app.route("/data")
def data():
    return render_template("data.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)
