import { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Circle,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "./App.css";
const API_URL = "https://earth-sentinel-jfbd.onrender.com";
const sensorIcon = L.icon({
  iconUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",

  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",

  shadowUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",

  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const menuItems = [
  { id: "dashboard", icon: "⌂", label: "Dashboard" },
  { id: "gis", icon: "⌖", label: "GIS Map" },
  { id: "locations", icon: "⌖", label: "Locations" },
  { id: "reporting", icon: "◉", label: "Reporting" },
  { id: "alerts", icon: "⚠", label: "Alerts" },
];

function App() {
  const [activePage, setActivePage] = useState("dashboard");

  const [backendStatus, setBackendStatus] = useState("Checking...");
  const [riskData, setRiskData] = useState(null);
  const [error, setError] = useState("");

  const loadRiskData = async () => {
    try {
      const response = await fetch(`${API_URL}/api/risk/current`);

      if (!response.ok) {
        throw new Error("Risk API unavailable");
      }

      const data = await response.json();

      if (data.status === "ok") {
        setRiskData(data);
        setBackendStatus("AI Backend Online");
        setError("");
      }
    } catch (err) {
      setBackendStatus("Backend Offline");
      setError("Unable to connect to Earth Sentinel backend.");
    }
  };

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await fetch(`${API_URL}/api/health`);

        if (!response.ok) {
          throw new Error("Backend unavailable");
        }

        setBackendStatus("AI Backend Online");
        await loadRiskData();
      } catch (err) {
        setBackendStatus("Backend Offline");
        setError(
          "Start FastAPI on port 8000 to connect the dashboard."
        );
      }
    };

    checkBackend();

    const interval = setInterval(loadRiskData, 5000);

    return () => clearInterval(interval);
  }, []);

  const overall = riskData?.overall;
  const ai = riskData?.ai;
  const sensor = riskData?.sensor;
  const sensors = riskData?.sensors;
  const location = riskData?.location;

  const renderDashboard = () => (
    <>
      <section className="hero">
        <div>
          <h1>
            Real-Time Landslide
            <span> Risk Monitoring</span>
          </h1>

          <p>
            Combining AI predictions, terrain intelligence
            and live sensor data.
          </p>
        </div>

        {overall && (
          <div className="hero-risk">
            <span>OVERALL RISK</span>

            <strong>{overall.risk_score}</strong>

            <label>{overall.risk_level}</label>
          </div>
        )}
      </section>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <section className="stats-grid">

        <div className="stat-card">
          <span>Rainfall</span>

          <strong>
            {sensors ? `${sensors.rainfall_mm} mm` : "--"}
          </strong>

          <small>Real-time sensor</small>
        </div>

        <div className="stat-card">
          <span>Soil Moisture</span>

          <strong>
            {sensors ? `${sensors.soil_moisture}%` : "--"}
          </strong>

          <small>Real-time sensor</small>
        </div>

        <div className="stat-card">
          <span>Ground Tilt</span>

          <strong>
            {sensors ? `${sensors.tilt_deg}°` : "--"}
          </strong>

          <small>IMU sensor</small>
        </div>

        <div className="stat-card">
          <span>Vibration</span>

          <strong>
            {sensors ? sensors.vibration : "--"}
          </strong>

          <small>Vibration sensor</small>
        </div>

      </section>

      <section className="content-grid">

        <div className="panel">

          <div className="panel-title">
            <h2>AI Risk Analysis</h2>

            <span className="live-badge">
              LIVE
            </span>
          </div>

          {ai ? (
            <>
              <div className="risk-score">
                <strong>{ai.risk_score}</strong>
                <span>/ 100</span>
              </div>

              <div className="risk-level">
                {ai.risk_level}
              </div>

              <div className="probability">
                AI Probability:{" "}
                {(ai.probability * 100).toFixed(1)}%
              </div>

              <div className="terrain-info">

                <div>
                  <span>Elevation</span>

                  <strong>
                    {ai.features.elevation_m.toFixed(1)} m
                  </strong>
                </div>

                <div>
                  <span>Slope</span>

                  <strong>
                    {ai.features.slope_deg.toFixed(2)}°
                  </strong>
                </div>

                <div>
                  <span>Aspect</span>

                  <strong>
                    {Math.round(
                      Math.atan2(
                        ai.features.aspect_sin,
                        ai.features.aspect_cos
                      ) *
                        (180 / Math.PI) +
                        360
                    ) % 360}
                    °
                  </strong>
                </div>

              </div>
            </>
          ) : (
            <div className="empty-state">
              Waiting for AI prediction...
            </div>
          )}

        </div>

        <div className="panel">

          <div className="panel-title">
            <h2>Sensor Risk</h2>

            <span className="live-badge">
              LIVE
            </span>
          </div>

          {sensor ? (
            <>
              <div className="risk-score">
                <strong>{sensor.risk_score}</strong>
                <span>/ 100</span>
              </div>

              <div className="risk-level">
                {sensor.condition}
              </div>

              {sensor.warnings.length > 0 ? (
                <div className="warnings">

                  {sensor.warnings.map(
                    (warning, index) => (
                      <div
                        key={index}
                        className="warning"
                      >
                        ⚠ {warning}
                      </div>
                    )
                  )}

                </div>
              ) : (
                <div className="normal-message">
                  ✓ All sensor conditions normal
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">
              Waiting for sensor data...
            </div>
          )}

        </div>

      </section>

      <section className="panel overall-panel">

        <div className="panel-title">
          <h2>Overall Risk Assessment</h2>

          <span className="live-badge">
            REAL-TIME
          </span>
        </div>

        {overall ? (
          <div className="overall-content">

            <div className="overall-score">
              {overall.risk_score}
            </div>

            <div>
              <div className="overall-level">
                {overall.risk_level}
              </div>

              <p>
                Combined assessment from XGBoost AI
                and real-time environmental sensors.
              </p>
            </div>

          </div>
        ) : (
          <div className="empty-state">
            Waiting for risk assessment...
          </div>
        )}

      </section>

      <section className="panel">

        <div className="panel-title">
          <h2>Current Sensor Location</h2>
        </div>

        {location ? (
          <div className="location-card">

            <div>
              <span>Latitude</span>

              <strong>
                {location.latitude}
              </strong>
            </div>

            <div>
              <span>Longitude</span>

              <strong>
                {location.longitude}
              </strong>
            </div>

          </div>
        ) : (
          <div className="empty-state">
            Waiting for GPS location...
          </div>
        )}

      </section>
    </>
  );

  const renderPlaceholder = (
    icon,
    title,
    description
  ) => (
    <section className="feature-page">

      <div className="feature-icon">
        {icon}
      </div>

      <h1>{title}</h1>

      <p>{description}</p>

      <div className="feature-status">
        MODULE READY
      </div>

    </section>
  );

  const renderPage = () => {

    if (activePage === "dashboard") {
      return renderDashboard();
    }

    if (activePage === "gis") {
      return (
        <section className="gis-page">

        <div className="gis-header">

        <div>
          <h1>GIS Risk Map</h1>

          <p>
            Real-time visualization of monitored
            locations and environmental risk.
          </p>
        </div>

        {overall && (
          <div className="map-risk-badge">
            <span>CURRENT RISK</span>
            <strong>
              {overall.risk_score}
            </strong>
            <label>
              {overall.risk_level}
            </label>
          </div>
        )}

      </div>

      {location ? (
        <div className="map-container">

          <MapContainer
            center={[
              location.latitude,
              location.longitude,
            ]}
            zoom={11}
            scrollWheelZoom={true}
            className="earth-map"
          >

            <TileLayer
              attribution='&copy; OpenStreetMap contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            <Circle
              center={[
                location.latitude,
                location.longitude,
              ]}
              radius={5000}
              pathOptions={{
                color: "#19d5bc",
                fillColor: "#19d5bc",
                fillOpacity: 0.08,
              }}
            />

            <Marker
              position={[
                location.latitude,
                location.longitude,
              ]}
              icon={sensorIcon}
            >

              <Popup>

                <div className="map-popup">

                  <strong>
                    Earth Sentinel Sensor
                  </strong>

                  <span>
                    ESP32-EARTH-SENTINEL-01
                  </span>

                  <span>
                    Latitude:{" "}
                    {location.latitude}
                  </span>

                  <span>
                    Longitude:{" "}
                    {location.longitude}
                  </span>

                  {overall && (
                    <span>
                      Risk:{" "}
                      {overall.risk_score}/100
                    </span>
                  )}

                </div>

              </Popup>

            </Marker>

          </MapContainer>

        </div>
      ) : (
        <div className="map-empty">
          Waiting for sensor GPS location...
        </div>
      )}

      <div className="map-info-grid">

        <div className="map-info-card">

          <span>MONITORED SENSOR</span>

          <strong>
            ESP32-EARTH-SENTINEL-01
          </strong>

          <small>
            Live sensor location
          </small>

        </div>

        <div className="map-info-card">

          <span>LOCATION</span>

          <strong>
            {location
              ? `${location.latitude}, ${location.longitude}`
              : "--"}
          </strong>

          <small>
            GPS coordinates
          </small>

        </div>

        <div className="map-info-card">

          <span>RISK STATUS</span>

          <strong>
            {overall
              ? overall.risk_level
              : "--"}
          </strong>

          <small>
            AI + sensor fusion
          </small>

        </div>

      </div>

    </section>
  );
}

    if (activePage === "locations") {
      return renderPlaceholder(
        "⌖",
        "Sensor Locations",
        "View deployed Earth Sentinel sensors, their GPS coordinates and latest readings."
      );
    }

    if (activePage === "reporting") {
      return renderPlaceholder(
        "◉",
        "Field Incident Reporting",
        "Capture a photograph, GPS location and field observation from a mobile device."
      );
    }

    if (activePage === "alerts") {
      return renderPlaceholder(
        "⚠",
        "Alerts",
        "View risk warnings and important environmental events detected by Earth Sentinel."
      );
    }

    return renderDashboard();
  };

  return (
    <div className="app">

      <header className="header">

        <div>
          <div className="brand">
            EARTH SENTINEL
          </div>

          <div className="subtitle">
            AI-Based Landslide Early Warning &
            Risk Monitoring System
          </div>
        </div>

        <div className="backend-status">
          <span className="status-dot"></span>
          {backendStatus}
        </div>

      </header>

      <div className="app-layout">

        <aside className="sidebar">

          <div className="sidebar-title">
            MONITORING
          </div>

          <nav>

            {menuItems.map((item) => (
              <button
                key={item.id}
                className={
                  activePage === item.id
                    ? "nav-item active"
                    : "nav-item"
                }
                onClick={() =>
                  setActivePage(item.id)
                }
              >
                <span className="nav-icon">
                  {item.icon}
                </span>

                <span>
                  {item.label}
                </span>
              </button>
            ))}

          </nav>

        </aside>

        <main className="dashboard">

          <div className="page-heading">

            <div>
              <span className="page-section">
                EARTH SENTINEL
              </span>

              <h2>
                {menuItems.find(
                  (item) =>
                    item.id === activePage
                )?.label}
              </h2>
            </div>

          </div>

          {renderPage()}

          <div className="prototype-notice">
            Prototype system — AI and sensor fusion
            results are intended for demonstration and
            further validation.
          </div>

        </main>

      </div>

      <nav className="mobile-nav">

        {menuItems.map((item) => (
          <button
            key={item.id}
            className={
              activePage === item.id
                ? "mobile-nav-item active"
                : "mobile-nav-item"
            }
            onClick={() =>
              setActivePage(item.id)
            }
          >

            <span>
              {item.icon}
            </span>

            <small>
              {item.label}
            </small>

          </button>
        ))}

      </nav>

    </div>
  );
}

export default App;