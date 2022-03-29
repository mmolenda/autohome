from flask import Flask
from autohome import autohome

app = Flask(__name__)
ah = autohome.AutoHome()

@app.route('/ah/<action>', methods=['POST'])
def autohome(action: str):
    try:
        return getattr(ah, f'command_{action}')()
    except AttributeError:
        return {}, 404


if __name__ == '__main__':
    app.run()
