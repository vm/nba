import os
import subprocess
import sys

from flask.ext.script import Manager, Server, Shell

from nba import app

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

manager = Manager(app)

# Turn on debugger and reloader by default.
manager.add_command(
    "runserver", Server(use_debugger=app.config['DEBUG'],
                        use_reloader=app.config['USE_RELOADER']))

# Serve up a basic app shell.
manager.add_command("shell", Shell())


@manager.command
def runtests():
    """Runs tests in /tests/."""
    subprocess.call("cd tests && py.test", shell=True)


if __name__ == "__main__":
    manager.run()
