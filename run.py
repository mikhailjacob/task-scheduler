"""Entry point for the Work Scheduler application.

Run this file directly to start the development server::

    python run.py

The server starts on http://localhost:5000 with debug mode enabled.
"""

from backend import create_app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
