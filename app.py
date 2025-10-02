from flask import Flask, send_from_directory
from flask_cors import CORS
from routes.data_routes import data_bp
from routes.recommend_routes import recommend_bp
import os

app = Flask(__name__)
CORS(app)  # Enable CORS so frontend can call API

# Register API blueprints
app.register_blueprint(data_bp, url_prefix="/data")
app.register_blueprint(recommend_bp, url_prefix="/recommend")

# Serve frontend index.html
@app.route('/')
def serve_frontend():
    return send_from_directory('frontend', 'index.html')

# Serve other frontend static files (CSS, JS)
@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join('frontend', path)):
        return send_from_directory('frontend', path)
    return "File not found", 404

if __name__ == "__main__":
    app.run(debug=True)
