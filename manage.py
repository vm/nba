
import os
import subprocess
import sys

from flask.ext.script import Manager, Server

from statcruncher import app, settings

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

manager = Manager(app)

# Turn on debugger and reloader by default.
manager.add_command("runserver", Server(
    use_debugger = settings.DEBUG,
    use_reloader = settings.USE_RELOADER,
    host = '0.0.0.0')
)

manager.add_command("runtests",
    subprocess.call("cd tests && py.test", shell=True)
)

if __name__ == "__main__":
    manager.run()
