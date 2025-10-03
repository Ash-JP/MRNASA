from flask import Flask, send_from_directory
from flask_cors import CORS  # allow frontend-backend communication

from routes.data_routes import data_bp
from routes.recommend_routes import recommend_bp

# Initialize app
app = Flask(__name__, static_folder="frontend")
CORS(app)

# Register API routes
app.register_blueprint(data_bp, url_prefix="/api/data")
app.register_blueprint(recommend_bp, url_prefix="/api/recommend")

# Serve login page at root
@app.route("/")
def serve_login():
    return send_from_directory("frontend", "index.html")

# Serve other static frontend files (JS, CSS)
@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory("frontend", path)

if __name__ == "__main__":
    app.run(debug=True)
