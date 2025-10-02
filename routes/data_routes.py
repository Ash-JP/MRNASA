# routes/data_routes.py
from flask import Blueprint, jsonify

data_bp = Blueprint('data', __name__)

@data_bp.route('/city/<city_name>')
def get_city_data(city_name):
    # Dummy data, replace with NASA data logic later
    sample_data = {
        "city": city_name,
        "pollution": "Moderate",
        "heat_index": 32,
        "healthcare_facilities": 12,
        "electricity_coverage": "95%"
    }
    return jsonify(sample_data)
