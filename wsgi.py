from flask import Flask
from portalsubmissions import app as blueprint

app = Flask(__name__)
app.register_blueprint(blueprint)

if __name__ == "__main__":
    app.run()