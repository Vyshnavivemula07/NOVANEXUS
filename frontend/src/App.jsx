import { useEffect, useState } from "react";
import piexif from "piexifjs";
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

// Set to false when ESP32 sensor data is connected.
const DEMO_MODE = true;

const DEMO_AI = {
  risk_score: 78,
  risk_level: "Critical",
  probability: 0.785,
  features: {
    elevation_m: 65.0,
    slope_deg: 15.49,
    aspect_sin: Math.sin((353 * Math.PI) / 180),
    aspect_cos: Math.cos((353 * Math.PI) / 180),
  },
};

const DEMO_SENSOR = {
  rainfall_mm: 72.5,
  soil_moisture: 71,
  tilt_deg: 6.4,
  vibration: 0.62,
  risk_score: 53,
  condition: "Warning",
  warnings: [
    "Elevated rainfall: 72.5 mm",
    "Elevated soil moisture: 71%",
    "Elevated ground tilt: 6.4°",
    "Elevated vibration: 0.62",
  ],
};

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

  const [backendStatus, setBackendStatus] =
    useState("Checking...");

  const [riskData, setRiskData] = useState(null);

  const [error, setError] = useState("");

  const [browserLocation, setBrowserLocation] =
    useState(null);

  const [locationStatus, setLocationStatus] =
    useState("Detecting location...");

  const [incidents, setIncidents] = useState([]);
  const [incidentsLoading, setIncidentsLoading] = useState(false);

  const [reportPhoto, setReportPhoto] = useState(null);
  const [reportPreview, setReportPreview] = useState("");
  const [reportLocation, setReportLocation] = useState(null);
  const [reportLocationStatus, setReportLocationStatus] = useState("Waiting for GPS...");
  const [reportType, setReportType] = useState("Slope Crack");
  const [reportDescription, setReportDescription] = useState("");
  const [reportMessage, setReportMessage] = useState("");
  const [reportSubmitting, setReportSubmitting] = useState(false);

  // -------------------------------------------------
  // Get risk data from deployed Render backend
  // using browser GPS location
  // -------------------------------------------------

  const loadRiskData = async () => {
    try {
      let url = `${API_URL}/api/risk/current`;

      if (browserLocation) {
        url +=
          `?latitude=${browserLocation.latitude}` +
          `&longitude=${browserLocation.longitude}`;
      }

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(
          `Risk API error: ${response.status}`
        );
      }

      const data = await response.json();

      if (data.status === "ok") {
        setRiskData(data);
        setBackendStatus("AI Backend Online");
        setError("");
      } else {
        setRiskData(null);
        setError(
          data.message || "Risk data unavailable"
        );
      }
    } catch (err) {
      console.error("Risk data error:", err);

      setBackendStatus("Backend Offline");

      setError(
        "Unable to connect to Earth Sentinel backend."
      );
    }
  };

  // -------------------------------------------------
  // Detect browser GPS location
  // -------------------------------------------------

  useEffect(() => {
    if (!navigator.geolocation) {
      setLocationStatus(
        "Geolocation not supported"
      );
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const {
          latitude,
          longitude,
          accuracy,
        } = position.coords;

        setBrowserLocation({
          latitude,
          longitude,
          accuracy,
        });

        setLocationStatus(
          "Browser GPS location detected"
        );
      },

      (error) => {
        console.error(
          "Geolocation error:",
          error
        );

        setLocationStatus(
          "Location permission required"
        );
      },

      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 30000,
      }
    );
  }, []);

  // -------------------------------------------------
  // Check deployed backend health
  // -------------------------------------------------

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await fetch(
          `${API_URL}/api/health`
        );

        if (!response.ok) {
          throw new Error(
            "Backend unavailable"
          );
        }

        setBackendStatus(
          "AI Backend Online"
        );
      } catch (err) {
        console.error(
          "Backend health error:",
          err
        );

        setBackendStatus(
          "Backend Offline"
        );

        setError(
          "Unable to connect to Earth Sentinel backend."
        );
      }
    };

    checkBackend();
  }, []);

  // -------------------------------------------------
  // Load risk whenever GPS location changes
  // and refresh every 5 seconds
  // -------------------------------------------------

  useEffect(() => {
    loadRiskData();

    const interval = setInterval(() => {
      loadRiskData();
    }, 5000);

    return () => clearInterval(interval);
  }, [browserLocation]);

  // -------------------------------------------------
  // Extract API data
  // -------------------------------------------------

  const overall = riskData?.overall;
  const ai = riskData?.ai;
  const sensor = riskData?.sensor;
  const displayAi = DEMO_MODE ? DEMO_AI : ai;

  const sensors = DEMO_MODE
    ? DEMO_SENSOR
    : riskData?.sensors;

  const displaySensor = DEMO_MODE
    ? { available: true, ...DEMO_SENSOR }
    : sensor;

  // Demo fusion: 65% AI + 25% sensor + 10% incident evidence.
  const displayOverall = DEMO_MODE && displayAi
    ? {
        risk_score: Math.round(
          displayAi.risk_score * 0.65 +
          DEMO_SENSOR.risk_score * 0.25 +
          15 * 0.10
        ),
        risk_level: "High",
        fusion_status: "Demo: AI + Sensor + Incident Evidence",
      }
    : overall;

  const sensorLocation = riskData?.location;

  const location =
    browserLocation || sensorLocation;

  // -------------------------------------------------
  // Geo-tagged incident reporting
  // -------------------------------------------------

  const captureReportLocation = () => {
    if (!navigator.geolocation) {
      setReportLocationStatus("Geolocation is not supported by this device");
      return;
    }

    setReportLocationStatus("Capturing GPS location...");

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude, accuracy } = position.coords;
        setReportLocation({ latitude, longitude, accuracy });
        setReportLocationStatus("GPS location captured");
      },
      (geoError) => {
        console.error("Incident GPS error:", geoError);
        setReportLocation(null);
        setReportLocationStatus("GPS permission required — photo cannot be submitted");
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
  };

  useEffect(() => {
    if (activePage === "reporting") {
      setReportMessage("");
      captureReportLocation();
    }
  }, [activePage]);

  const loadIncidents = async () => {
    try {
      setIncidentsLoading(true);
      const response = await fetch(`${API_URL}/api/incidents`);
      if (!response.ok) throw new Error(`Incident API error: ${response.status}`);
      const data = await response.json();
      setIncidents(data.data || []);
    } catch (error) {
      console.error("Incident load error:", error);
      setReportMessage("Unable to load stored incidents from backend.");
    } finally {
      setIncidentsLoading(false);
    }
  };

  useEffect(() => {
    loadIncidents();
  }, []);

  const handleReportPhoto = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setReportPhoto(file);
    setReportMessage("");

    const reader = new FileReader();
    reader.onload = () => setReportPreview(reader.result);
    reader.readAsDataURL(file);
  };

  const toDms = (value) => {
    const absolute = Math.abs(value);
    const degrees = Math.floor(absolute);
    const minutesFloat = (absolute - degrees) * 60;
    const minutes = Math.floor(minutesFloat);
    const seconds = Math.round((minutesFloat - minutes) * 60 * 100);
    return [[degrees, 1], [minutes, 1], [seconds, 100]];
  };

  const createGeoTaggedImage = (file, gps) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const imageData = reader.result;
          const image = new Image();
          image.onload = () => {
            const canvas = document.createElement("canvas");
            canvas.width = image.naturalWidth;
            canvas.height = image.naturalHeight;
            const context = canvas.getContext("2d");
            context.drawImage(image, 0, 0);
            const jpegData = canvas.toDataURL("image/jpeg", 0.92);
            const exif = piexif.load(jpegData);
            const gpsIfd = {};
            gpsIfd[piexif.GPSIFD.GPSLatitudeRef] = gps.latitude >= 0 ? "N" : "S";
            gpsIfd[piexif.GPSIFD.GPSLatitude] = toDms(gps.latitude);
            gpsIfd[piexif.GPSIFD.GPSLongitudeRef] = gps.longitude >= 0 ? "E" : "W";
            gpsIfd[piexif.GPSIFD.GPSLongitude] = toDms(gps.longitude);
            gpsIfd[piexif.GPSIFD.GPSMapDatum] = "WGS-84";
            gpsIfd[piexif.GPSIFD.GPSDateStamp] = new Date().toISOString().slice(0, 10).replaceAll("-", ":");
            exif.GPS = gpsIfd;
            const exifBytes = piexif.dump(exif);
            resolve(piexif.insert(exifBytes, jpegData));
          };
          image.onerror = reject;
          image.src = imageData;
        } catch (error) {
          reject(error);
        }
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

  const submitIncident = async (event) => {
    event.preventDefault();

    if (!reportPhoto) {
      setReportMessage("Please select an incident photo.");
      return;
    }

    if (!reportLocation) {
      setReportMessage("GPS location is required. Capture GPS before submitting the photo.");
      return;
    }

    setReportSubmitting(true);
    setReportMessage("");

    try {
      const geoTaggedPhoto = await createGeoTaggedImage(reportPhoto, reportLocation);
      const incident = {
        id: `INC-${Date.now()}`,
        photo: geoTaggedPhoto,
        original_filename: reportPhoto.name,
        latitude: Number(reportLocation.latitude.toFixed(7)),
        longitude: Number(reportLocation.longitude.toFixed(7)),
        gps_accuracy_m: Number(reportLocation.accuracy.toFixed(1)),
        timestamp: new Date().toISOString(),
        incident_type: reportType,
        description: reportDescription.trim(),
        geotagged: true,
      };

      const response = await fetch(`${API_URL}/api/incidents`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(incident),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Incident API error: ${response.status} ${errorText}`);
      }

      const result = await response.json();
      setIncidents((current) => [result.data, ...current.filter((item) => item.id !== result.data.id)]);
      setReportPhoto(null);
      setReportPreview("");
      setReportDescription("");
      setReportMessage("✓ Geo-tagged incident stored in backend and added to the GIS map.");
    } catch (error) {
      console.error("Incident submission error:", error);
      setReportMessage("Unable to geo-tag this image. Please try another photo.");
    } finally {
      setReportSubmitting(false);
    }
  };

  // -------------------------------------------------
  // Dashboard
  // -------------------------------------------------

  const renderDashboard = () => (
    <>
      <section className="hero">
        <div>
          <h1>
            Real-Time Landslide
            <span> Risk Monitoring</span>
          </h1>

          <p>
            Combining AI predictions, terrain
            intelligence and live sensor data.
          </p>
        </div>

        {displayOverall && (
          <div className="hero-risk">
            <span>OVERALL RISK</span>

            <strong>
              {displayOverall.risk_score}
            </strong>

            <label>
              {displayOverall.risk_level}
            </label>
          </div>
        )}
      </section>

      {error && !DEMO_MODE && (
        <div className="error-message">
          {error}
        </div>
      )}

      {DEMO_MODE && (
        <div className="normal-message" style={{ marginBottom: "18px" }}>
          DEMO MODE — sensor values below are simulated until the ESP32 is connected.
        </div>
      )}

      <section className="stats-grid">

        <div className="stat-card">
          <span>Rainfall</span>

          <strong>
            {sensors?.rainfall_mm != null
              ? `${sensors.rainfall_mm} mm`
              : "--"}
          </strong>

          <small>
            {DEMO_MODE ? "Demo sensor" : "Real-time sensor"}
          </small>
        </div>

        <div className="stat-card">
          <span>Soil Moisture</span>

          <strong>
            {sensors?.soil_moisture != null
              ? `${sensors.soil_moisture}%`
              : "--"}
          </strong>

          <small>
            {DEMO_MODE ? "Demo sensor" : "Real-time sensor"}
          </small>
        </div>

        <div className="stat-card">
          <span>Ground Tilt</span>

          <strong>
            {sensors?.tilt_deg != null
              ? `${sensors.tilt_deg}°`
              : "--"}
          </strong>

          <small>
            {DEMO_MODE ? "Demo IMU" : "IMU sensor"}
          </small>
        </div>

        <div className="stat-card">
          <span>Vibration</span>

          <strong>
            {sensors?.vibration != null
              ? sensors.vibration
              : "--"}
          </strong>

          <small>
            {DEMO_MODE ? "Demo sensor" : "Vibration sensor"}
          </small>
        </div>

      </section>

      <section className="content-grid">

        {/* AI RISK */}

        <div className="panel">

          <div className="panel-title">
            <h2>AI Risk Analysis</h2>

            <span className="live-badge">
              LIVE
            </span>
          </div>

          {displayAi ? (
            <>
              <div className="risk-score">
                <strong>
                  {displayAi.risk_score}
                </strong>

                <span>
                  / 100
                </span>
              </div>

              <div className="risk-level">
                {displayAi.risk_level}
              </div>

              <div className="probability">
                AI Probability:{" "}
                {(displayAi.probability * 100).toFixed(1)}
                %
              </div>

              <div className="terrain-info">

                <div>
                  <span>
                    Elevation
                  </span>

                  <strong>
                    {displayAi.features.elevation_m.toFixed(
                      1
                    )}{" "}
                    m
                  </strong>
                </div>

                <div>
                  <span>
                    Slope
                  </span>

                  <strong>
                    {displayAi.features.slope_deg.toFixed(
                      2
                    )}°
                  </strong>
                </div>

                <div>
                  <span>
                    Aspect
                  </span>

                  <strong>
                    {Math.round(
                      (
                        Math.atan2(
                          displayAi.features.aspect_sin,
                          displayAi.features.aspect_cos
                        ) *
                          (180 / Math.PI) +
                        360
                      ) % 360
                    )}
                    °
                  </strong>
                </div>

              </div>

              <div className="normal-message">
                Location:{" "}
                {riskData?.location_source ||
                  "Monitoring location"}
              </div>
            </>
          ) : (
            <div className="empty-state">
              Waiting for AI prediction...
            </div>
          )}

        </div>

        {/* SENSOR RISK */}

        <div className="panel">

          <div className="panel-title">
            <h2>Sensor Risk</h2>

            <span className="live-badge">
              {DEMO_MODE ? "DEMO" : "LIVE"}
            </span>
          </div>

          {displaySensor?.available ? (
            <>
              <div className="risk-score">
                <strong>
                  {displaySensor.risk_score}
                </strong>

                <span>
                  / 100
                </span>
              </div>

              <div className="risk-level">
                {displaySensor.condition}
              </div>

              {displaySensor.warnings?.length > 0 ? (
                <div className="warnings">

                  {displaySensor.warnings.map(
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

      {/* OVERALL RISK */}

      <section className="panel overall-panel">

        <div className="panel-title">
          <h2>
            Overall Risk Assessment
          </h2>

          <span className="live-badge">
            {DEMO_MODE ? "DEMO MODE" : "REAL-TIME"}
          </span>
        </div>

        {displayOverall ? (
          <div className="overall-content">

            <div className="overall-score">
              {displayOverall.risk_score}
            </div>

            <div>

              <div className="overall-level">
                {displayOverall.risk_level}
              </div>

              <p>
                {displayOverall.fusion_status ||
                  "Risk assessment generated by Earth Sentinel."}
              </p>

            </div>

          </div>
        ) : (
          <div className="empty-state">
            Waiting for risk assessment...
          </div>
        )}

      </section>

      {/* LOCATION */}

      <section className="panel">

        <div className="panel-title">
          <h2>
            Current Monitoring Location
          </h2>
        </div>

        {location ? (
          <div className="location-card">

            <div>
              <span>
                Latitude
              </span>

              <strong>
                {location.latitude}
              </strong>
            </div>

            <div>
              <span>
                Longitude
              </span>

              <strong>
                {location.longitude}
              </strong>
            </div>

            <div>
              <span>
                Location Source
              </span>

              <strong>
                {browserLocation
                  ? "Browser GPS"
                  : "Backend Sensor"}
              </strong>
            </div>

            {browserLocation?.accuracy && (
              <div>
                <span>
                  GPS Accuracy
                </span>

                <strong>
                  ±
                  {Math.round(
                    browserLocation.accuracy
                  )}{" "}
                  m
                </strong>
              </div>
            )}

          </div>
        ) : (
          <div className="empty-state">
            {locationStatus}
          </div>
        )}

      </section>
    </>
  );

  // -------------------------------------------------
  // Placeholder pages
  // -------------------------------------------------

  const renderPlaceholder = (
    icon,
    title,
    description
  ) => (
    <section className="feature-page">

      <div className="feature-icon">
        {icon}
      </div>

      <h1>
        {title}
      </h1>

      <p>
        {description}
      </p>

      <div className="feature-status">
        MODULE READY
      </div>

    </section>
  );

  // -------------------------------------------------
  // Page routing
  // -------------------------------------------------

  const renderPage = () => {

    if (activePage === "dashboard") {
      return renderDashboard();
    }

    // -------------------------------------------------
    // GIS MAP
    // -------------------------------------------------

    if (activePage === "gis") {

      return (
        <section className="gis-page">

          <div className="gis-header">

            <div>

              <h1>
                GIS Risk Map
              </h1>

              <p>
                Real-time visualization of
                monitored locations and
                environmental risk.
              </p>

            </div>

            {overall && (
              <div className="map-risk-badge">

                <span>
                  CURRENT RISK
                </span>

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
                  attribution="&copy; OpenStreetMap contributors"
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
                        Earth Sentinel Location
                      </strong>

                      <span>
                        {browserLocation
                          ? "Browser GPS Location"
                          : "Sensor Location"}
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
                          {overall.risk_score}
                          /100
                        </span>
                      )}

                    </div>

                  </Popup>

                </Marker>

                {incidents.map((incident) => (
                  <Marker
                    key={incident.id}
                    position={[incident.latitude, incident.longitude]}
                    icon={sensorIcon}
                  >
                    <Popup>
                      <div className="map-popup">
                        <strong>Geo-tagged Incident</strong>
                        <span>Type: {incident.incident_type}</span>
                        <span>{incident.description || "No description"}</span>
                        <span>Latitude: {incident.latitude}</span>
                        <span>Longitude: {incident.longitude}</span>
                        <span>GPS Accuracy: ±{incident.gps_accuracy_m} m</span>
                        <img src={incident.photo} alt="Incident" style={{ width: "160px", borderRadius: "8px", marginTop: "6px" }} />
                      </div>
                    </Popup>
                  </Marker>
                ))}

              </MapContainer>

            </div>

          ) : (

            <div className="map-empty">
              Waiting for GPS location...
            </div>

          )}

          <div className="map-info-grid">

            <div className="map-info-card">

              <span>
                MONITORED SENSOR
              </span>

              <strong>
                ESP32-EARTH-SENTINEL-01
              </strong>

              <small>
                Live sensor location
              </small>

            </div>

            <div className="map-info-card">

              <span>
                LOCATION
              </span>

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

              <span>
                RISK STATUS
              </span>

              <strong>
                {overall
                  ? overall.risk_level
                  : "--"}
              </strong>

              <small>
                {overall?.fusion_status ||
                  "Risk assessment"}
              </small>

            </div>

          </div>

        </section>
      );
    }

    // -------------------------------------------------
    // LOCATIONS
    // -------------------------------------------------

    if (activePage === "locations") {

      return renderPlaceholder(
        "⌖",
        "Sensor Locations",
        "View deployed Earth Sentinel sensors, their GPS coordinates and latest readings."
      );
    }

    // -------------------------------------------------
    // REPORTING
    // -------------------------------------------------

    if (activePage === "reporting") {
      return (
        <section className="reporting-page">
          <div className="reporting-header">
            <div>
              <h1>Field Incident Reporting</h1>
              <p>Capture a photograph with GPS coordinates, timestamp and field observations.</p>
            </div>
            <div className={reportLocation ? "gps-status ready" : "gps-status"}>
              <span>●</span> {reportLocationStatus}
            </div>
          </div>

          <form className="report-form" onSubmit={submitIncident}>
            <div className="report-grid">
              <div className="report-photo-box">
                {reportPreview ? (
                  <img src={reportPreview} alt="Incident preview" className="report-preview" />
                ) : (
                  <div className="photo-placeholder">
                    <div className="feature-icon">◉</div>
                    <strong>Incident Photograph</strong>
                    <span>Photo is required for every incident</span>
                  </div>
                )}
                <label className="photo-button">
                  {reportPhoto ? "Change Photo" : "Take / Upload Photo"}
                  <input type="file" accept="image/*" capture="environment" onChange={handleReportPhoto} hidden />
                </label>
              </div>

              <div className="report-fields">
                <div className="field-group">
                  <label>Incident Type</label>
                  <select value={reportType} onChange={(e) => setReportType(e.target.value)}>
                    <option>Slope Crack</option>
                    <option>Rockfall</option>
                    <option>Soil Movement</option>
                    <option>Road Damage</option>
                    <option>Water Seepage</option>
                    <option>Other</option>
                  </select>
                </div>

                <div className="field-group">
                  <label>Description</label>
                  <textarea
                    value={reportDescription}
                    onChange={(e) => setReportDescription(e.target.value)}
                    placeholder="Describe the field observation..."
                    rows="5"
                  />
                </div>

                <div className="gps-card">
                  <div>
                    <span>LATITUDE</span>
                    <strong>{reportLocation ? reportLocation.latitude.toFixed(7) : "--"}</strong>
                  </div>
                  <div>
                    <span>LONGITUDE</span>
                    <strong>{reportLocation ? reportLocation.longitude.toFixed(7) : "--"}</strong>
                  </div>
                  <div>
                    <span>GPS ACCURACY</span>
                    <strong>{reportLocation ? `±${Math.round(reportLocation.accuracy)} m` : "--"}</strong>
                  </div>
                </div>

                <button type="button" className="gps-button" onClick={captureReportLocation}>
                  Refresh GPS Location
                </button>

                <button type="submit" className="submit-report" disabled={!reportPhoto || !reportLocation || reportSubmitting}>
                  {reportSubmitting ? "Saving Geo-tagged Incident..." : "Submit Geo-tagged Incident"}
                </button>

                {reportMessage && <div className="report-message">{reportMessage}</div>}
              </div>
            </div>
          </form>

          <div className="panel incident-list-panel">
            <div className="panel-title">
              <h2>Saved Incidents</h2>
              <span className="live-badge">{incidents.length} REPORT{incidents.length === 1 ? "" : "S"}</span>
            </div>
            {incidentsLoading ? (
              <div className="empty-state">Loading stored incidents...</div>
            ) : incidents.length === 0 ? (
              <div className="empty-state">No field incidents reported yet.</div>
            ) : (
              <div className="incident-list">
                {incidents.map((incident) => (
                  <div className="incident-row" key={incident.id}>
                    <img src={incident.photo} alt={incident.incident_type} />
                    <div>
                      <strong>{incident.incident_type}</strong>
                      <span>{incident.description || "No description provided"}</span>
                      <small>{incident.latitude}, {incident.longitude} · ±{incident.gps_accuracy_m} m</small>
                    </div>
                    <small>{new Date(incident.timestamp).toLocaleString()}</small>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      );
    }

    // -------------------------------------------------
    // ALERTS
    // -------------------------------------------------

    if (activePage === "alerts") {

      return renderPlaceholder(
        "⚠",
        "Alerts",
        "View risk warnings and important environmental events detected by Earth Sentinel."
      );
    }

    return renderDashboard();
  };

  // -------------------------------------------------
  // Main UI
  // -------------------------------------------------

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
                {
                  menuItems.find(
                    (item) =>
                      item.id === activePage
                  )?.label
                }
              </h2>

            </div>

          </div>

          {renderPage()}

          <div className="prototype-notice">
            Prototype system — AI and sensor
            fusion results are intended for
            demonstration and further validation.
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