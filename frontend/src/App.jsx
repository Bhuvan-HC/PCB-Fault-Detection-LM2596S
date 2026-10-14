
import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";

const API_URL = "http://10.52.100.29:8000";

const initialReadings = {
  vin: null,
  vout: null,
  current: null,
  temperature: null,
  connected: false,
};

function formatValue(value, decimals = 3) {
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(Number(value))
  ) {
    return "--";
  }

  return Number(value).toFixed(decimals);
}

function MeasurementCard({ title, value, unit, decimals = 3 }) {
  return (
    <article className="measurement-card">
      <div className="measurement-label">{title}</div>
      <div className="measurement-value">
        <span>{formatValue(value, decimals)}</span>
        <span className="measurement-unit">{unit}</span>
      </div>
    </article>
  );
}

export default function App() {
  const fileInputRef = useRef(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [originalImage, setOriginalImage] = useState("");
  const [annotatedImage, setAnnotatedImage] = useState("");
  const [detections, setDetections] = useState([]);
  const [detecting, setDetecting] = useState(false);
  const [imageError, setImageError] = useState("");
  const [imageSuccess, setImageSuccess] = useState("");

  const [readings, setReadings] = useState(initialReadings);
  const [sensorError, setSensorError] = useState("");
  const [lastUpdate, setLastUpdate] = useState(null);

  // Refresh sensor values every second.
  const fetchReadings = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/readings`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      setReadings({
        vin: data.vin ?? null,
        vout: data.vout ?? null,
        current: data.current ?? null,
        temperature: data.temperature ?? null,
        connected: Boolean(data.connected),
      });

      setLastUpdate(new Date());
      setSensorError("");
    } catch {
      setReadings((previous) => ({
        ...previous,
        connected: false,
      }));
      setSensorError("Unable to connect to the sensor backend.");
    }
  }, []);

  useEffect(() => {
    fetchReadings();

    const intervalId = setInterval(fetchReadings, 1000);

    return () => clearInterval(intervalId);
  }, [fetchReadings]);

  // Select a PCB image.
  function handleFileChange(event) {
    const file = event.target.files?.[0];

    if (!file) return;

    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setImageError("Please select a JPG, PNG, or WEBP image.");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setImageError("Image size must not exceed 10 MB.");
      return;
    }

    setSelectedFile(file);
    setOriginalImage(URL.createObjectURL(file));
    setAnnotatedImage("");
    setDetections([]);
    setImageError("");
    setImageSuccess("");
  }

  // Upload the image to the existing YOLO backend.
  async function handleDetection() {
    if (!selectedFile) {
      setImageError("Please upload a PCB image first.");
      return;
    }

    setDetecting(true);
    setImageError("");
    setImageSuccess("");

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch(`${API_URL}/api/process-image`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "YOLO detection failed.");
      }

      setDetections(data.detections || []);
      setAnnotatedImage(data.image || "");
      setImageSuccess("PCB image processing completed successfully.");
    } catch (error) {
      setImageError(
        error.message || "Unable to process the image. Check the backend."
      );
    } finally {
      setDetecting(false);
    }
  }

  function clearImage() {
    if (originalImage) {
      URL.revokeObjectURL(originalImage);
    }

    setSelectedFile(null);
    setOriginalImage("");
    setAnnotatedImage("");
    setDetections([]);
    setImageError("");
    setImageSuccess("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  useEffect(() => {
    return () => {
      if (originalImage) {
        URL.revokeObjectURL(originalImage);
      }
    };
  }, [originalImage]);

  return (
    <main className="dashboard">
      {/* Dashboard header */}
      <header className="header">
        <div>
          <div className="eyebrow">AI + EMBEDDED SYSTEMS</div>
          <h1>PCB Fault Detection System</h1>
          <p className="subtitle">
            YOLO-based visual inspection and live electrical monitoring
            for the LM2596S PCB.
          </p>
        </div>

        <div className="status-badge">Dashboard Active</div>
      </header>

      {/* Electrical readings: only four cards */}
      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>Electrical Measurements</h2>
            <p>Live ESP32 sensor readings.</p>
          </div>

          <span
            className={`connection ${readings.connected ? "connected" : "disconnected"
              }`}
          >
            {readings.connected ? "ESP32 Online" : "ESP32 Offline"}
          </span>
        </div>

        <div className="sensor-grid measurements-grid">
          <MeasurementCard
            title="Input Voltage"
            value={readings.vin}
            unit="V"
          />

          <MeasurementCard
            title="Output Voltage"
            value={readings.vout}
            unit="V"
          />

          <MeasurementCard
            title="Current"
            value={readings.current}
            unit="A"
          />

          <MeasurementCard
            title="Temperature"
            value={readings.temperature}
            unit="°C"
            decimals={2}
          />
        </div>

        <div className="sensor-update-info" aria-live="polite">
          {sensorError ||
            (lastUpdate
              ? `Last refreshed: ${lastUpdate.toLocaleTimeString()}`
              : "Waiting for sensor readings...")}
        </div>
      </section>

      {/* YOLO visual inspection: retained */}
      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>PCB Visual Inspection</h2>
            <p>
              Upload a PCB image to detect visible components and defects
              using your trained YOLO model.
            </p>
          </div>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={handleFileChange}
          hidden
        />

        <button
          className="upload-button"
          type="button"
          onClick={() => fileInputRef.current?.click()}
        >
          Choose PCB Image
        </button>

        {selectedFile && (
          <p className="filename">
            Selected file: {selectedFile.name}
          </p>
        )}

        <div className="image-grid">
          <div className="image-card">
            <h3>Original PCB Image</h3>

            {originalImage ? (
              <img
                className="pcb-image"
                src={originalImage}
                alt="Original PCB"
              />
            ) : (
              <div className="image-placeholder">
                Upload a PCB image to begin inspection.
              </div>
            )}
          </div>

          <div className="image-card">
            <h3>YOLO Detection Result</h3>

            {annotatedImage ? (
              <img
                className="pcb-image"
                src={annotatedImage}
                alt="YOLO annotated PCB"
              />
            ) : (
              <div className="image-placeholder">
                YOLO bounding boxes and predictions will appear here.
              </div>
            )}
          </div>
        </div>

        <button
          className="detect-button"
          type="button"
          onClick={handleDetection}
          disabled={!selectedFile || detecting}
        >
          {detecting ? "Processing Image..." : "Detect PCB Faults"}
        </button>

        {imageError && (
          <div className="alert error" role="alert">
            {imageError}
          </div>
        )}

        {imageSuccess && (
          <div className="alert success" role="status">
            {imageSuccess}
          </div>
        )}

        {/* YOLO prediction results */}
        {annotatedImage && (
          <div className="results">
            <h3>Detection Results ({detections.length})</h3>

            {detections.length > 0 ? (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Class</th>
                      <th>Confidence</th>
                      <th>Bounding Box (x1, y1, x2, y2)</th>
                    </tr>
                  </thead>

                  <tbody>
                    {detections.map((detection, index) => {
                      const box = detection.box;

                      return (
                        <tr key={`${detection.class_id}-${index}`}>
                          <td>{detection.class_name}</td>
                          <td>
                            {(detection.confidence * 100).toFixed(2)}%
                          </td>
                          <td>
                            {box
                              ? `${box.x1}, ${box.y1}, ${box.x2}, ${box.y2}`
                              : "--"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="subtitle">
                No objects were detected at the current confidence threshold.
              </p>
            )}

            <button
              className="secondary-button"
              type="button"
              onClick={clearImage}
            >
              Clear Image
            </button>
          </div>
        )}
      </section>

      <footer>
        AI-Powered Automated PCB Fault Detection and Component-Level
        Fault Localization System
      </footer>
    </main>
  );
}
