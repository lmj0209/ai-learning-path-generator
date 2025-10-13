#!/usr/bin/env python3
"""Initialize database tables for production deployment."""
import os
from web_app import create_app, db

# Create Flask app
app = create_app()

with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print("✅ Database tables created successfully!")
