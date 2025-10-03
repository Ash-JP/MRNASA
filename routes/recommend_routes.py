from flask import Blueprint, request, jsonify
from services.planning_service import recommend_facility

recommend_bp = Blueprint("recommend", __name__)

@recommend_bp.route("/facility", methods=["POST"])
def recommend_facility_route():
    data = request.json
    facility_type = data.get("type", "hospital")
    city = data.get("city", "Sample City")
    role = data.get("role", "Citizen")  # Get role from request

    recommendation = recommend_facility(facility_type, city, role)
    return jsonify(recommendation)
