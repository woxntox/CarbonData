from flask import Flask
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.secret_key = os.getenv('SECRET_KEY', 'vantablack-secret-key')
    
    # Initialize plugin manager
    from .plugin_loader import PluginManager
    app.plugin_manager = PluginManager()
    
    # Register blueprints
    from .routes import main
    app.register_blueprint(main, url_prefix='')
    
    return app
