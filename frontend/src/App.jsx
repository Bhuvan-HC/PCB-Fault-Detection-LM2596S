import { useRef, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

export default function App() {
  const fileInputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [resultImage, setResultImage] = useState("");
  const [detections, setDetections] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [readings, setReadings] = useState({
    vin: null,
    vout: null,
    current: null,
    connected: false,
  });

  function handleFileChange(event) {
    const selectedFile = event.target.files?.[0];

    if (!selectedFile) return;

    if (!selectedFile.type.startsWith("image/")) {
      setError("Please select an image file.");
      return;
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      setError("Image size must be less than 10 MB.");
      return;
    }

    setFile(selectedFile);
    setPreview(URL.createObjectURL(selectedFile));

    setResultImage("");
    setDetections([]);
    setError("");
    setMessage("");
  }

  async function detectFaults() {
    if (!file) {
      setError("Please upload a PCB image first.");
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");
    setResultImage("");
    setDetections([]);

    try {
      const formData = new FormData();

      formData.append("file", file);

      const response = await fetch(
        `${API_URL}/api/process-image`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || data.message || "Detection failed."
        );
      }

      if (!data.success) {
        throw new Error(data.message || "Detection failed.");
      }

      setResultImage(data.image || "");
      setDetections(data.detections || []);
      setMessage(
        data.detected
          ? `Detection completed: ${data.detections.length} object(s) found.`
          : "Detection completed. No objects detected."
      );
    } catch (err) {
      setError(
        err.message ||
        "Cannot connect to the backend. Check whether FastAPI is running."
      );
    } finally {
      setLoading(false);
    }
  }

  async function fetchReadings() {
    try {
      const response = await fetch(
        `${API_URL}/api/readings`
      );

      if (!response.ok) {
        throw new Error("Could not fetch sensor readings.");
      }

      const data = await response.json();

      setReadings(data);
    } catch {
      setReadings((previous) => ({
        ...previous,
        connected: false,
      }));
    }
  }

  return (
    <main className="dashboard">
      <header className="header">
        <div>
          <p className="eyebrow">AI-POWERED INSPECTION</p>
          <h1>PCB Fault Detection</h1>
          <p className="subtitle">
            Upload a PCB image to inspect visible faults.
          </p>
        </div>

        <span className="status-badge">
          YOLO Vision
        </span>
      </header>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>PCB Image Inspection</h2>
            <p>
              Upload a JPG, PNG, or WebP image.
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
          onClick={() => fileInputRef.current?.click()}
          type="button"
        >
          Choose PCB Image
        </button>

        {file && (
          <p className="filename">
            Selected: {file.name}
          </p>
        )}

        <div className="image-grid">
          <div className="image-card">
            <h3>Original Image</h3>

            {preview ? (
              <img
                src={preview}
                alt="Original PCB"
                className="pcb-image"
              />
            ) : (
              <div className="image-placeholder">
                <span>Upload a PCB image</span>
              </div>
            )}
          </div>

          <div className="image-card">
            <h3>YOLO Detection Result</h3>

            {resultImage ? (
              <img
                src={resultImage}
                alt="PCB with YOLO detection boxes"
                className="pcb-image"
              />
            ) : (
              <div className="image-placeholder">
                <span>
                  Detection result will appear here
                </span>
              </div>
            )}
          </div>
        </div>

        <button
          className="detect-button"
          onClick={detectFaults}
          disabled={!file || loading}
          type="button"
        >
          {loading ? "Detecting..." : "Detect Faults"}
        </button>

        {error && (
          <div className="alert error">
            {error}
          </div>
        )}

        {message && (
          <div className="alert success">
            {message}
          </div>
        )}

        {detections.length > 0 && (
          <div className="results">
            <h3>Detected Objects</h3>

            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Fault</th>
                    <th>Confidence</th>
                    <th>Bounding Box</th>
                  </tr>
                </thead>

                <tbody>
                  {detections.map((item, index) => (
                    <tr key={`${item.class_id}-${index}`}>
                      <td>{item.class_name}</td>

                      <td>
                        {(item.confidence * 100).toFixed(1)}%
                      </td>

                      <td>
                        {item.box.join(", ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      <section className="panel sensor-panel">
        <div className="section-heading">
          <div>
            <h2>Electrical Measurements</h2>
            <p>
              This module is independent of image detection.
            </p>
          </div>

          <span
            className={
              readings.connected
                ? "connection connected"
                : "connection disconnected"
            }
          >
            {readings.connected
              ? "Connected"
              : "Offline"}
          </span>
        </div>

        <div className="sensor-grid">
          <SensorCard
            label="Input Voltage"
            value={readings.vin}
            unit="V"
          />

          <SensorCard
            label="Output Voltage"
            value={readings.vout}
            unit="V"
          />

          <SensorCard
            label="Current"
            value={readings.current}
            unit="A"
          />
        </div>

        <button
          className="secondary-button"
          onClick={fetchReadings}
          type="button"
        >
          Refresh Readings
        </button>
      </section>

      <footer>
        PCB Fault Detection System · YOLO + FastAPI
      </footer>
    </main>
  );
}

function SensorCard({ label, value, unit }) {
  return (
    <div className="sensor-card">
      <p>{label}</p>

      <strong>
        {value === null || value === undefined
          ? "--"
          : Number(value).toFixed(2)}{" "}
        <span>{unit}</span>
      </strong>
    </div>
  );
}