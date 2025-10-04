from flask import Flask, render_template
import folium
import os
import webbrowser

app = Flask(__name__)

def create_map():
    # Center on Delhi as example
    m = folium.Map(location=[28.6139, 77.2090], zoom_start=12, tiles="OpenStreetMap")

    # Marker
    folium.Marker([28.6139, 77.2090], popup="Delhi", tooltip="Click").add_to(m)

    # Circle
    folium.Circle([28.6139, 77.2090], radius=1000, fill=True).add_to(m)

    # Polygon example
    folium.Polygon(locations=[[28.62,77.20],[28.61,77.22],[28.60,77.21]],
                   popup="Example polygon",
                   tooltip="Polygon").add_to(m)

    # Return HTML representation which we will embed into the template
    return m._repr_html_()

@app.route("/")
def index():
    map_html = create_map()
    return render_template("index.html", map_html=map_html)

if __name__ == "__main__":
    # Optionally auto-open browser (comment out if you don't want this)
    url = "http://127.0.0.1:5000"
    # only open if not in a production WSGI env
    if os.environ.get("WERKZEUG_RUN_MAIN") is None:
        try:
            webbrowser.open(url)
        except:
            pass

    app.run(host="127.0.0.1", port=5000, debug=True)
