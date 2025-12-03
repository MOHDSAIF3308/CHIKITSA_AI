# run.py
from app import app

if __name__ == '__main__':
    # Development: debug mode, auto-reload
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=True
    )