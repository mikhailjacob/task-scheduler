"""Entry point for the Work Scheduler application.

Run this file directly to start the development server::

    python run.py

The server starts on http://localhost:5000.  Set the environment
variable ``FLASK_DEBUG=1`` to enable the interactive debugger.
"""

import os

from backend import create_app

if __name__ == "__main__":
    app = create_app()
    is_debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(debug=is_debug, port=5000)
