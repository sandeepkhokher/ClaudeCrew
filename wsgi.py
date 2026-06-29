"""WSGI entrypoint.

Local dev:   flask --app wsgi run -p 8765
Production:  gunicorn wsgi:app
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(port=8765, debug=True)
