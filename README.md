# MR NASA: Enhancing Urban Resilience with NASA Data

## Project Overview
*MR NASA* is an interactive, web-based tool designed to help urban planners, researchers, and citizens *visualize, analyze, and make data-driven decisions for sustainable urban development*.  
The platform leverages *NASA Earth Observation data, AI analytics, and geospatial visualization* to assess climate, vegetation, nightlights, and environmental suitability for urban infrastructure placement.

Users can:
- Explore city-scale *temperature, vegetation, and nightlight data*
- Place virtual infrastructure (houses, hospitals, schools, parks, water plants)
- Receive *climate suitability scores* and actionable recommendations

---

## Team

- *Team Lead:* Niranjan S  
- *Team Members:*
  - Aashray J Pramod  
  - Anand M S  
  - Sofiya B  
  - Minnah PK  
  - Rifa K  

College of Engineering Attingal, India  
IEEE Student Branch  

---

Disclamiar:
Login in username: planner
password: plannerpass

## Features

1. 🌍 *Interactive Map*
   - Layers: Temperature (MODIS LST), Night Lights (VIIRS), Vegetation (NDVI), Heatmap

2. 🔍 *Location Search*
   - Search for cities or coordinates using the *Leaflet Geocoder*

3. 🏗 *Infrastructure Placement*
   - Place structures: houses, schools, hospitals, parks, water treatment plants
   - Drag, edit, and remove markers

4. 📊 *Climate Suitability Analysis*
   - Compute suitability scores based on NASA POWER climate data
   - Generate heatmaps and detailed recommendations

5. 🤖 *AI-Powered Recommendations*
   - Uses Python scripts to compute optimal placement based on environmental data

---

## NASA & External Resources Used

- *NASA GIBS (Global Imagery Browse Services)*  
  - MODIS Terra LST & NDVI layers

- *VIIRS Night Lights Data*  
  - Urban activity and population density insights

- *NASA POWER API*  
  - Climate variables: temperature, precipitation, humidity, solar radiation, wind

- *Geospatial Data*
  - Roads, water bodies, and coordinates for mapping

---

## Technology Stack

- *Frontend*
  - HTML5, CSS3, JavaScript
  - [Leaflet.js](https://leafletjs.com/) for interactive maps
  - [Leaflet Control Geocoder](https://github.com/perliedman/leaflet-control-geocoder)
  - [Leaflet Heat](https://github.com/Leaflet/Leaflet.heat) for heatmaps

- *Backend*
  - Python 3.x
  - Flask framework
  - REST APIs to fetch NASA POWER data

- *Database*
  - Local JSON / in-memory storage for placed structure points

- *Deployment*
  - Render / Heroku (cloud hosting)

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/mr-nasa.git
   cd mr-nasa

2. Create a Python virtual environment:

python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows


3. Install dependencies:

pip install -r requirements.txt


4. Run the Flask app:

python app.py


5. Open your browser and navigate to:

http://127.0.0.1:5000




---

Usage

1. Use the top toolbar or sidebar search bar to find a location.


2. Select a time range (start and end dates) for NASA data.


3. Toggle map layers for Temperature, Night Lights, Vegetation, and Heatmap.


4. Select a structure type and click Place Structure, then click on the map to add it.


5. Click Analyze Selected Points to compute suitability scores.


6. View recommendations, heatmaps, and detailed analysis for each point.




---

Future Enhancements

Real-time AI predictions for urban heat and climate risks

Integration with citizen feedback and IoT sensors

3D urban modeling using LiDAR data

Global expansion to other cities with automated data fetching



---

License

This project is for educational and research purposes. Please contact the team for collaboration or commercial use.


---

Contact

Team Lead: Niranjan S
Email: niranjansajeev68@gmail.com

Project repository maintained by the MR NASA Team.

---

✅ This README includes:  
- Project overview and objectives  
- Team and roles  
- Features and technical stack  
- NASA and external resources used  
- Installation and usage instructions  
- Future enhancements  

