from flask import Flask
from autohome import autohome

app = Flask(__name__)
ah = autohome.AutoHome()

@app.route('/ah/<action>')
def autohome(action: str):
    try:
        return getattr(ah, f'command_{action}')()
    except AttributeError:
        return {}, 404
