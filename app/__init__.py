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
    userinfo = get_userinfo(username)
    if userinfo and 'uid' in userinfo:
        suggestions = TwitchClient.get_similar_streams(userinfo['uid'])
    else:
        suggestions = None

    return suggestions
