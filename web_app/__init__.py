import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from werkzeug.middleware.proxy_fix import ProxyFix

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # Route for @login_required
login_manager.login_message_category = 'info'
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # If the app is running behind a proxy (like on Render), fix the WSGI environment
    if os.environ.get('RENDER'):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Set DEV_MODE from environment
    app.config['DEV_MODE'] = os.environ.get('DEV_MODE', 'False').lower() == 'true'
    if app.config['DEV_MODE']:
        print("\033[93m⚠️  Running in DEV_MODE - API calls will be stubbed!\033[0m")

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Import and register blueprints
    from web_app.main_routes import bp as main_bp
    app.register_blueprint(main_bp)

    from web_app.auth_routes import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from web_app.api_endpoints import api_bp
    app.register_blueprint(api_bp)

    # Import models here to ensure they are registered with SQLAlchemy
    from web_app import models
    
    # Google OAuth blueprint (Flask-Dance)
    from web_app.google_oauth import google_bp, bp as google_auth_bp
    # Register Flask-Dance blueprint at /login/google
    app.register_blueprint(google_bp, url_prefix="/login")
    # Register our auth blueprint for callbacks and helper routes under /auth
    app.register_blueprint(google_auth_bp, url_prefix="/auth")
    
    # Flask-Dance will use session storage by default
    # This works better for our use case since we create the user in our callback

    return app
