import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'digidara-one-super-secret-jwt-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Allow local SQLite fallback, otherwise connect to PostgreSQL
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        # Check standard default DATABASE_URL or environment
        DATABASE_URL = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///digidara_one.db')
        
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'digidara-one-jwt-secret')
