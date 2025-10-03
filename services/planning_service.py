# services/planning_service.py

def recommend_facility(facility_type, city):
    # Dummy recommendation logic
    sample_recommendations = {
        "hospital": f"A new {facility_type} should be placed in the northern part of {city} where healthcare coverage is low.",
        "school": f"Consider building a {facility_type} in the eastern side of {city}, where population density is growing.",
        "power_station": f"{city} needs an additional {facility_type} near industrial zones to handle electricity demand.",
        "park": f"A green {facility_type} is recommended in the central {city} area to reduce heat islands."
    }

    return {
        "city": city,
        "facility": facility_type,
        "recommendation": sample_recommendations.get(
            facility_type.lower(),
            f"No specific recommendation for {facility_type}, but general improvement needed in {city}."
        )
    }
