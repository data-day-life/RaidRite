from flask import Flask
from app.controllers import blueprints
from flask import render_template
from app.twitch_client import TwitchClient, get_userinfo

app = Flask(__name__, template_folder='../templates')

for blueprint in blueprints:
    app.register_blueprint(blueprint)

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/user/<username>')
def suggestions(username):
    suggested_raids = None
    try:
        userinfo = get_userinfo(username)
        if userinfo and 'uid' in userinfo:
            suggested_raids = TwitchClient(userinfo['uid'], num_suggestions=10).get_similar_streams()

    except ValueError:
        pass

    return suggested_raids
