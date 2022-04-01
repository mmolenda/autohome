from flask import Flask
from autohome import autohome

app = Flask(__name__)

@app.route('/ah/<action>', methods=['POST'])
def ah(action: str):
    try:
        ah = autohome.AutoHome()
        return getattr(ah, f'command_{action}')()
    except AttributeError:
        return {}, 404


if __name__ == '__main__':
    app.run()
