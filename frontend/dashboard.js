const API_BASE = "http://127.0.0.1:5000/api";

// Display output in page
function showOutput(id, data) {
  const el = document.getElementById(id);
  if (el) {
    el.textContent = JSON.stringify(data, null, 2);
  }
}

// Fetch pollution data
function getPollution() {
  fetch(`${API_BASE}/data/pollution`)
    .then(res => res.json())
    .then(data => showOutput("data-output", data))
    .catch(err => console.error("Error fetching pollution:", err));
}

// Fetch heat data
function getHeat() {
  fetch(`${API_BASE}/data/heat`)
    .then(res => res.json())
    .then(data => showOutput("data-output", data))
    .catch(err => console.error("Error fetching heat:", err));
}

// Fetch healthcare data
function getHealthcare() {
  fetch(`${API_BASE}/data/healthcare`)
    .then(res => res.json())
    .then(data => showOutput("data-output", data))
    .catch(err => console.error("Error fetching healthcare:", err));
}

// Recommend facility
function recommendFacility(event) {
  event.preventDefault();

  const facility = document.getElementById("facility").value;
  const city = document.getElementById("city").value;
  const role = localStorage.getItem("userRole") || "Citizen"; // get role

  fetch(`${API_BASE}/recommend/facility`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ type: facility, city: city, role: role })
  })
    .then(res => res.json())
    .then(data => showOutput("recommend-output", data))
    .catch(err => console.error(err));
}

