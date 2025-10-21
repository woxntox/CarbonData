from app import create_app

app = create_app()

if __name__ == '__main__':
    # Bind to localhost and disable debug/reloader to avoid macOS permission issues
    app.run(host='127.0.0.1', port=5003, debug=False, use_reloader=False)
