let map;
let drawnLayers;
let selectedPoints = [];
let heatLayer = null;
let activeLayers = {};
let currentDate = null;

const GIBS_CONFIG = {
    baseUrl: 'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/',
    layers: {
        temperature: {
            name: 'MODIS_Terra_Land_Surface_Temp_Day',
            tileMatrixSet: 'EPSG4326_2km',
            maxZoom: 7,
            attribution: 'NASA GIBS MODIS LST',
            opacity: 0.65
        },
        nightLights: {
            name: 'VIIRS_SNPP_DayNightBand_ENCC',
            tileMatrixSet: 'EPSG4326_500m',
            maxZoom: 8,
            attribution: 'NASA GIBS VIIRS Night Lights',
            opacity: 0.8
        },
        vegetation: {
            name: 'MODIS_Terra_NDVI_8Day',
            tileMatrixSet: 'EPSG4326_1km',
            maxZoom: 8,
            attribution: 'NASA GIBS MODIS NDVI',
            opacity: 0.7
        }
    }
};

function getAvailableDate(daysBack = 3) {
    const date = new Date();
    date.setDate(date.getDate() - daysBack);
    return date.toISOString().slice(0, 10);
}

function createGIBSTileUrl(layerConfig, date) {
    const { name, tileMatrixSet } = layerConfig;
    return `${GIBS_CONFIG.baseUrl}${name}/default/${date}/${tileMatrixSet}/{z}/{y}/{x}.png`;
}

function initMap() {
    try {
        map = L.map('map', {
            center: [20.5937, 78.9629],
            zoom: 5,
            zoomControl: true
        });

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(map);

        drawnLayers = L.layerGroup().addTo(map);
        currentDate = getAvailableDate();

        initializeGIBSLayers();

        if (typeof L.heatLayer === 'function') {
            heatLayer = L.layerGroup();
        } else {
            console.warn('Leaflet.heat plugin not loaded');
            heatLayer = L.layerGroup();
        }

        if (typeof L.Control !== 'undefined' && L.Control.geocoder) {
            L.Control.geocoder({
                defaultMarkGeocode: false,
                placeholder: 'Search location...',
                errorMessage: 'Location not found'
            })
            .on('markgeocode', function(e) {
                const latlng = e.geocode.center;
                map.setView(latlng, 12);
                L.popup()
                    .setLatLng(latlng)
                    .setContent(e.geocode.name)
                    .openOn(map);
            })
            .addTo(map);
        }

        setupEventListeners();
        setDefaultDates();

        console.log('Map initialized with date:', currentDate);
    } catch (error) {
        console.error('Error initializing map:', error);
        alert('Failed to initialize map. Please refresh the page.');
    }
}

function initializeGIBSLayers() {
    try {
        activeLayers.temperature = L.tileLayer(
            createGIBSTileUrl(GIBS_CONFIG.layers.temperature, currentDate),
            {
                maxZoom: GIBS_CONFIG.layers.temperature.maxZoom,
                attribution: GIBS_CONFIG.layers.temperature.attribution,
                opacity: GIBS_CONFIG.layers.temperature.opacity
            }
        ).addTo(map);

        activeLayers.nightLights = L.tileLayer(
            createGIBSTileUrl(GIBS_CONFIG.layers.nightLights, currentDate),
            {
                maxZoom: GIBS_CONFIG.layers.nightLights.maxZoom,
                attribution: GIBS_CONFIG.layers.nightLights.attribution,
                opacity: GIBS_CONFIG.layers.nightLights.opacity
            }
        );

        activeLayers.vegetation = L.tileLayer(
            createGIBSTileUrl(GIBS_CONFIG.layers.vegetation, currentDate),
            {
                maxZoom: GIBS_CONFIG.layers.vegetation.maxZoom,
                attribution: GIBS_CONFIG.layers.vegetation.attribution,
                opacity: GIBS_CONFIG.layers.vegetation.opacity
            }
        );

        console.log('GIBS layers initialized');
    } catch (error) {
        console.error('Error initializing GIBS layers:', error);
    }
}

function updateGIBSLayersWithDate(dateStr) {
    try {
        currentDate = dateStr;
        console.log('Updating layers to date:', dateStr);

        if (activeLayers.temperature) {
            const wasActive = map.hasLayer(activeLayers.temperature);
            map.removeLayer(activeLayers.temperature);
            activeLayers.temperature = L.tileLayer(
                createGIBSTileUrl(GIBS_CONFIG.layers.temperature, dateStr),
                {
                    maxZoom: GIBS_CONFIG.layers.temperature.maxZoom,
                    attribution: GIBS_CONFIG.layers.temperature.attribution,
                    opacity: GIBS_CONFIG.layers.temperature.opacity
                }
            );
            if (wasActive) activeLayers.temperature.addTo(map);
        }

        if (activeLayers.nightLights) {
            const wasActive = map.hasLayer(activeLayers.nightLights);
            map.removeLayer(activeLayers.nightLights);
            activeLayers.nightLights = L.tileLayer(
                createGIBSTileUrl(GIBS_CONFIG.layers.nightLights, dateStr),
                {
                    maxZoom: GIBS_CONFIG.layers.nightLights.maxZoom,
                    attribution: GIBS_CONFIG.layers.nightLights.attribution,
                    opacity: GIBS_CONFIG.layers.nightLights.opacity
                }
            );
            if (wasActive) activeLayers.nightLights.addTo(map);
        }

        if (activeLayers.vegetation) {
            const wasActive = map.hasLayer(activeLayers.vegetation);
            map.removeLayer(activeLayers.vegetation);
            activeLayers.vegetation = L.tileLayer(
                createGIBSTileUrl(GIBS_CONFIG.layers.vegetation, dateStr),
                {
                    maxZoom: GIBS_CONFIG.layers.vegetation.maxZoom,
                    attribution: GIBS_CONFIG.layers.vegetation.attribution,
                    opacity: GIBS_CONFIG.layers.vegetation.opacity
                }
            );
            if (wasActive) activeLayers.vegetation.addTo(map);
        }

        console.log('Layers updated');
    } catch (error) {
        console.error('Error updating layers:', error);
    }
}

function setupEventListeners() {
    setupLayerToggle('layer-modis', 'temperature');
    setupLayerToggle('layer-viirs', 'nightLights');
    setupLayerToggle('layer-ndvi', 'vegetation');
    setupLayerToggle('layer-heatmap', 'analysisHeat');

    const placeBtn = document.getElementById('place-structure');
    const structureSelect = document.getElementById('structure-type');
    
    if (placeBtn && structureSelect) {
        let placingMode = false;
        let clickHandler = null;

        placeBtn.addEventListener('click', () => {
            if (placingMode) {
                placingMode = false;
                map.off('click', clickHandler);
                placeBtn.textContent = 'Click to Place Structure';
                placeBtn.classList.remove('active');
                map.getContainer().style.cursor = '';
            } else {
                placingMode = true;
                const structureType = structureSelect.value;
                placeBtn.textContent = 'Cancel Placement';
                placeBtn.classList.add('active');
                map.getContainer().style.cursor = 'crosshair';

                clickHandler = (e) => {
                    placeStructure(e.latlng, structureType);
                    placingMode = false;
                    placeBtn.textContent = 'Click to Place Structure';
                    placeBtn.classList.remove('active');
                    map.getContainer().style.cursor = '';
                    map.off('click', clickHandler);
                };

                map.once('click', clickHandler);
            }
        });
    }

    const scoreBtn = document.getElementById('score-selected');
    if (scoreBtn) {
        scoreBtn.addEventListener('click', analyzePoints);
    }

    const endDateInput = document.getElementById('end-date');
    if (endDateInput) {
        endDateInput.addEventListener('change', (e) => {
            if (e.target.value) {
                updateGIBSLayersWithDate(e.target.value);
            }
        });
    }

    const modalClose = document.getElementById('rec-close');
    if (modalClose) {
        modalClose.addEventListener('click', () => {
            const modal = document.getElementById('rec-modal');
            if (modal) modal.style.display = 'none';
        });
    }

    const modal = document.getElementById('rec-modal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
}

function setupLayerToggle(checkboxId, layerKey) {
    const checkbox = document.getElementById(checkboxId);
    if (!checkbox) return;

    checkbox.addEventListener('change', (e) => {
        if (layerKey === 'analysisHeat') {
            if (e.target.checked) {
                if (heatLayer) heatLayer.addTo(map);
            } else {
                if (heatLayer) map.removeLayer(heatLayer);
            }
        } else {
            const layer = activeLayers[layerKey];
            if (!layer) return;

            if (e.target.checked) {
                layer.addTo(map);
            } else {
                map.removeLayer(layer);
            }
        }
    });
}

function placeStructure(latlng, structureType) {
    const icons = {
        house: '🏠',
        hospital: '🏥',
        school: '🏫',
        park: '🌳',
        water: '💧'
    };

    const icon = L.divIcon({
        html: `<div style="font-size: 24px; text-shadow: 0 2px 4px rgba(0,0,0,0.5);">${icons[structureType] || '📍'}</div>`,
        className: 'custom-marker',
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });

    const marker = L.marker(latlng, {
        icon: icon,
        draggable: true
    }).addTo(drawnLayers);

    marker.structureType = structureType;

    const updatePopup = () => {
        const pos = marker.getLatLng();
        marker.setPopupContent(`
            <div style="min-width: 150px;">
                <b>${structureType.charAt(0).toUpperCase() + structureType.slice(1)}</b><br>
                <small>Lat: ${pos.lat.toFixed(6)}<br>Lon: ${pos.lng.toFixed(6)}</small><br>
                <button onclick="removeMarker(${drawnLayers.getLayerId(marker)})" 
                    style="margin-top: 5px; padding: 3px 8px; background: #ef4444; color: white; border: none; border-radius: 3px; cursor: pointer;">
                    Remove
                </button>
            </div>
        `);
    };

    updatePopup();
    marker.bindPopup();
    marker.on('dragend', updatePopup);
    marker.on('click', () => marker.openPopup());

    console.log(`Placed ${structureType} at`, latlng);
}

window.removeMarker = function(layerId) {
    drawnLayers.eachLayer((layer) => {
        if (drawnLayers.getLayerId(layer) === layerId) {
            drawnLayers.removeLayer(layer);
        }
    });
};

async function analyzePoints() {
    try {
        selectedPoints = [];
        drawnLayers.eachLayer((layer) => {
            if (layer.getLatLng && layer.structureType) {
                const latlng = layer.getLatLng();
                selectedPoints.push({
                    marker: layer,
                    lat: latlng.lat,
                    lon: latlng.lng,
                    type: layer.structureType
                });
            }
        });

        if (selectedPoints.length === 0) {
            alert('Please place at least one structure on the map before analyzing.');
            return;
        }

        const loading = document.getElementById('loading');
        if (loading) loading.style.display = 'block';

        const startInput = document.getElementById('start-date');
        const endInput = document.getElementById('end-date');
        const startDate = startInput && startInput.value ? startInput.value.replace(/-/g, '') : '';
        const endDate = endInput && endInput.value ? endInput.value.replace(/-/g, '') : '';

        const payload = {
            points: selectedPoints.map(p => ({
                lat: p.lat,
                lon: p.lon,
                type: p.type,
                ndvi: 0.3,
                population: 2000,
                road_km: 1.0,
                water_km: 2.0
            })),
            start: startDate,
            end: endDate
        };

        const response = await fetch('/api/hotspot_score', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        if (data.results && data.results.length > 0) {
            displayResults(data.results);
            updateAnalysisHeatmap(data.results);
        } else {
            alert('No results returned from analysis.');
        }

    } catch (error) {
        console.error('Analysis error:', error);
        alert(`Analysis failed: ${error.message}`);
    } finally {
        const loading = document.getElementById('loading');
        if (loading) loading.style.display = 'none';
    }
}

function displayResults(results) {
    const container = document.getElementById('recommendations');
    if (!container) return;

    container.innerHTML = '<h4 style="margin-bottom: 1rem; color: #2c3e50;">Analysis Results</h4>';
    
    window.__analysisResults = results;

    results.forEach((result, idx) => {
        const point = selectedPoints[idx];
        const structureType = point ? point.type : 'Unknown';
        
        const meanTemp = result.power_summary?.mean_temp;
        const meanPrecip = result.power_summary?.mean_precip;
        
        const scoreColor = result.score >= 70 ? '#10b981' : result.score >= 50 ? '#f59e0b' : '#ef4444';
        
        const div = document.createElement('div');
        div.className = 'rec';
        div.style.borderLeftColor = scoreColor;
        
        div.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                <b>${structureType.charAt(0).toUpperCase() + structureType.slice(1)} #${idx + 1}</b>
                <span style="background: ${scoreColor}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.85rem; font-weight: 600;">
                    ${result.score.toFixed(1)}
                </span>
            </div>
            <small style="display: block; margin-bottom: 0.5rem;">
                Location: ${result.lat.toFixed(4)}, ${result.lon.toFixed(4)}
            </small>
            <small style="display: block;">
                ${meanTemp !== undefined && meanTemp !== null ? `Temp: ${meanTemp.toFixed(1)}°C` : 'Temp: N/A'} | 
                ${meanPrecip !== undefined && meanPrecip !== null ? `Precip: ${meanPrecip.toFixed(1)}mm` : 'Precip: N/A'}
            </small>
            <button onclick="showDetailedAnalysis(${idx})">
                View Details
            </button>
        `;
        
        container.appendChild(div);
    });
}

function updateAnalysisHeatmap(results) {
    heatLayer.clearLayers();

    if (results.length === 0) return;

    let minTemp = Infinity;
    let maxTemp = -Infinity;
    
    results.forEach(r => {
        const temp = r.power_summary?.mean_temp;
        if (temp != null) {
            minTemp = Math.min(minTemp, temp);
            maxTemp = Math.max(maxTemp, temp);
        }
    });

    if (!isFinite(minTemp) || !isFinite(maxTemp)) {
        console.warn('No valid temperature data for heatmap');
        return;
    }

    results.forEach(r => {
        const temp = r.power_summary?.mean_temp;
        if (temp == null) return;

        const normalized = maxTemp > minTemp ? (temp - minTemp) / (maxTemp - minTemp) : 0.5;
        
        let color;
        if (normalized < 0.25) {
            color = '#3b82f6';
        } else if (normalized < 0.5) {
            color = '#22c55e';
        } else if (normalized < 0.65) {
            color = '#eab308';
        } else if (normalized < 0.8) {
            color = '#f97316';
        } else {
            color = '#ef4444';
        }

        const circle = L.circleMarker([r.lat, r.lon], {
            radius: 15,
            fillColor: color,
            color: '#ffffff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.7
        });

        circle.bindPopup(`
            <b>Temperature Analysis</b><br>
            Temp: ${temp.toFixed(1)}°C<br>
            Score: ${r.score.toFixed(1)}
        `);

        circle.addTo(heatLayer);
    });

    const heatCheckbox = document.getElementById('layer-heatmap');
    if (heatCheckbox && !heatCheckbox.checked) {
        heatCheckbox.checked = true;
        heatLayer.addTo(map);
    }

    console.log(`Heatmap updated with ${results.length} points (${minTemp.toFixed(1)}°C - ${maxTemp.toFixed(1)}°C)`);
}

window.showDetailedAnalysis = function(index) {
    const results = window.__analysisResults;
    if (!results || !results[index]) return;

    const result = results[index];
    const point = selectedPoints[index];
    const structureType = point ? point.type : 'Unknown';
    
    const modal = document.getElementById('rec-modal');
    const body = document.getElementById('rec-body');
    if (!modal || !body) return;

    const meanTemp = result.power_summary?.mean_temp;
    const meanPrecip = result.power_summary?.mean_precip;
    const nDays = result.power_summary?.n_days;
    
    const scoreColor = result.score >= 70 ? '#10b981' : result.score >= 50 ? '#f59e0b' : '#ef4444';
    
    let recommendation = '';
    if (result.score >= 70) {
        recommendation = 'Excellent location for infrastructure. High suitability based on climate and accessibility factors.';
    } else if (result.score >= 50) {
        recommendation = 'Moderate suitability. Consider additional site assessments and potential improvements.';
    } else {
        recommendation = 'Low suitability. This location may face significant challenges. Consider alternative sites.';
    }

    body.innerHTML = `
        <h3 style="color: #2c3e50; margin-bottom: 1.5rem;">
            ${structureType.charAt(0).toUpperCase() + structureType.slice(1)} Analysis
        </h3>
        
        <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 600;">Suitability Score</span>
                <span style="font-size: 1.5rem; font-weight: bold; color: ${scoreColor};">${result.score.toFixed(1)}</span>
            </div>
        </div>

        <p><b>Location:</b> ${result.lat.toFixed(6)}, ${result.lon.toFixed(6)}</p>
        
        <hr>
        
        <h4 style="color: #2c3e50; margin: 1rem 0 0.5rem 0;">Climate Data (NASA POWER)</h4>
        <p><b>Mean Temperature:</b> ${meanTemp !== undefined && meanTemp !== null ? meanTemp.toFixed(2) + '°C' : 'N/A'}</p>
        <p><b>Mean Precipitation:</b> ${meanPrecip !== undefined && meanPrecip !== null ? meanPrecip.toFixed(2) + 'mm/day' : 'N/A'}</p>
        <p><b>Data Points:</b> ${nDays || 'N/A'} days</p>
        
        <hr>
        
        <h4 style="color: #2c3e50; margin: 1rem 0 0.5rem 0;">Environmental Factors</h4>
        <p><b>NDVI (Vegetation):</b> ${result.ndvi.toFixed(2)}</p>
        <p><b>Population Density:</b> ~${result.population} people/km²</p>
        <p><b>Structure Type:</b> ${structureType}</p>
        
        <hr>
        
        <h4 style="color: #2c3e50; margin: 1rem 0 0.5rem 0;">Recommendation</h4>
        <p style="line-height: 1.6;">${recommendation}</p>
    `;

    modal.style.display = 'flex';
};

function setDefaultDates() {
    try {
        const startInput = document.getElementById('start-date');
        const endInput = document.getElementById('end-date');
        
        if (startInput && endInput) {
            const today = new Date();
            const thirtyDaysAgo = new Date(today);
            thirtyDaysAgo.setDate(today.getDate() - 30);
            
            endInput.valueAsDate = today;
            startInput.valueAsDate = thirtyDaysAgo;
        }
    } catch (error) {
        console.warn('Could not set default dates:', error);
    }
}

window.clearAllMarkers = function() {
    drawnLayers.clearLayers();
    selectedPoints = [];
    
    const recContainer = document.getElementById('recommendations');
    if (recContainer) {
        recContainer.innerHTML = '';
    }
    
    if (heatLayer) {
        heatLayer.clearLayers();
    }
    
    console.log('All markers cleared');
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMap);
} else {
    initMap();
}