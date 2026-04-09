import os
import redis
from rq import Queue
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

    # On Render: skip Flask-Migrate/Alembic entirely to avoid
    # "unable to infer type for attribute score" error from
    # Flask-Dance OAuthConsumerMixin + SQLAlchemy 2.0 + Alembic conflict
    if not os.environ.get('RENDER'):
        migrate.init_app(app, db)

    # Initialize Redis connection for RQ
    try:
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            raise ValueError("REDIS_URL not set, worker queue will not be available.")
        # ssl_cert_reqs=None is important for managed services like Upstash/Render Redis
        app.redis = redis.from_url(redis_url, ssl_cert_reqs=None)
        app.logger.info("Redis connection for RQ initialized successfully.")
    except Exception as e:
        app.logger.error(f"Failed to initialize Redis connection: {e}")
        app.redis = None

    # Import and register blueprints
    from web_app.main_routes import bp as main_bp
    app.register_blueprint(main_bp)

    from web_app.auth_routes import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from web_app.api_endpoints import api_bp
    app.register_blueprint(api_bp)

    # Import models here to ensure they are registered with SQLAlchemy
    from web_app import models

    # On Render: auto-create all tables if they don't exist
    if os.environ.get('RENDER'):
        with app.app_context():
            try:
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                existing_tables = inspector.get_table_names()
                if not existing_tables or 'users' not in existing_tables:
                    print("🔧 Creating database tables (first deploy)...")
                    db.create_all()
                    print("✅ Database tables created successfully!")
                else:
                    print(f"✅ Database tables already exist ({len(existing_tables)} tables)")
            except Exception as e:
                print(f"⚠️  Database table check/create: {e}")
                # Try create_all anyway
                try:
                    db.create_all()
                    print("✅ Database tables created (fallback)!")
                except Exception as e2:
                    print(f"⚠️  Could not create tables: {e2}")

    # Google OAuth blueprint (Flask-Dance)
    from web_app.google_oauth import google_bp, bp as google_auth_bp
    # Register Flask-Dance blueprint at /login/google
    app.register_blueprint(google_bp, url_prefix="/login")
    # Register our auth blueprint for callbacks and helper routes under /auth
    app.register_blueprint(google_auth_bp, url_prefix="/auth")

    return app
