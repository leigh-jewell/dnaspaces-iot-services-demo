activate_this = '/usr/local/venv/dnaspaces-iot-services-demo/bin/activate_this.py'

with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

import sys

sys.path.insert(0, "/var/www/dnas_step_tracker")

from app import app as application