"""
Lightweight Flask API for task management
Handles: task creation, status checking, result retrieval
"""
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for Vercel frontend

# Import routes
from backend.routes import api_bp
app.register_blueprint(api_bp, url_prefix='/api')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "api"}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
