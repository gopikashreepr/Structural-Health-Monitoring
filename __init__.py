import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flasgger import Swagger
from werkzeug.middleware.proxy_fix import ProxyFix
from config import config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
swagger = Swagger()

def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Proxy fix for deployment
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    
    # Swagger configuration
    app.config['SWAGGER'] = {
        'title': 'SHM API',
        'description': 'Structural Health Monitoring API',
        'version': '1.0.0',
        'uiversion': 3
    }
    swagger.init_app(app)
    
    # Register blueprints
    from routes.main import main_bp
    from routes.api import api_bp
    from routes.history import history_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(history_bp, url_prefix='/history')
    
    return app