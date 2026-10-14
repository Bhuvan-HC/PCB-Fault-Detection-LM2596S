
import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";
const MAX_FILE_SIZE = 10 * 1024 * 1024;

export default function App() {
  const fileInputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [resultImage, setResultImage] = useState("");
  const [detections, setDetections] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [apiOnline, setApiOnline] = useState(false);

  const [readings, setReadings] = useState({
    vin: null,
    vout: null,
    current: null,
    connected: false,
  });

  useEffect(() => {
    let active = true;

    async function checkApi() {
      try {
        const response = await fetch(`${API_URL}/health`);
        const data = await response.json();

        if (active) {
          setApiOnline(response.ok && data.yolo_loaded === true);
        }
      } catch {
        if (active) setApiOnline(false);
      }
    }

    checkApi();
    const interval = setInterval(checkApi, 5000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    return () => {
      if (preview.startsWith("blob:")) {
        URL.revokeObjectURL(preview);
      }
    };
  }, [preview]);

  function handleFileChange(event) {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) return;

    setError("");
    setMessage("");
    setResultImage("");
    setDetections([]);

    if (!selectedFile.type.startsWith("image/")) {
      setFile(null);
      setPreview("");
      setError("Please choose an image file.");
      return;
    }

    if (
      !["image/jpeg", "image/png", "image/webp"].includes(
        selectedFile.type
      )
    ) {
      setFile(null);
      setPreview("");
      setError("Supported formats: JPG, PNG, and WebP.");
      return;
    }

    if (selectedFile.size > MAX_FILE_SIZE) {
      setFile(null);
      setPreview("");
      setError("Image size must be less than 10 MB.");
      return;
    }

    setFile(selectedFile);
    setPreview(URL.createObjectURL(selectedFile));
  }

  async function detectObjects() {
    if (!file) {
      setError("Please choose a PCB image first.");
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

      const response = await fetch(`${API_URL}/api/process-image`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Image detection failed.");
      }

      if (!data.success) {
        throw new Error(data.message || "Image detection failed.");
      }

      setResultImage(data.image || "");
      setDetections(data.detections || []);
      setMessage(
        data.detected
          ? `Detection completed: ${data.count ?? data.detections.length} object(s) found.`
          : "No objects detected. Try a clearer image or check the trained model."
      );
    } catch (err) {
      setError(
        err.message ||
          "Cannot connect to FastAPI. Check that the backend is running."
      );
    } finally {
      setLoading(false);
    }
  }

  async function fetchReadings() {
    try {
      const response = await fetch(`${API_URL}/api/readings`);

      if (!response.ok) {
        throw new Error("Could not fetch sensor readings.");
      }

      setReadings(await response.json());
    } catch {
      setReadings((previous) => ({
        ...previous,
        connected: false,
      }));
    }
  }

  function resetImage() {
    setFile(null);
    setPreview("");
    setResultImage("");
    setDetections([]);
    setError("");
    setMessage("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  return (
    <main className="dashboard">
      <header className="header">
        <div>
          <p className="eyebrow">AI-POWERED PCB INSPECTION</p>
          <h1>PCB Fault Detection</h1>
          <p className="subtitle">
            Upload a PCB image to inspect it with your trained YOLO model.
          </p>
        </div>

        <span className="status-badge">
          {apiOnline ? "YOLO Online" : "YOLO Offline"}
        </span>
      </header>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>PCB Image Inspection</h2>
            <p>Supported formats: JPG, PNG, WebP · Maximum 10 MB</p>
          </div>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={handleFileChange}
          hidden
        />

        <div className="action-row">
          <button
            className="upload-button"
            onClick={() => fileInputRef.current?.click()}
            type="button"
            disabled={loading}
          >
            Choose PCB Image
          </button>

          <button
            className="secondary-button"
            onClick={resetImage}
            type="button"
            disabled={loading || (!file && !preview)}
          >
            Clear Image
          </button>
        </div>

        {file && <p className="filename">Selected: {file.name}</p>}

        <div className="image-grid">
          <div className="image-card">
            <h3>Original Image</h3>

            {preview ? (
              <img
                src={preview}
                alt="Uploaded PCB"
                className="pcb-image"
              />
            ) : (
              <div className="image-placeholder">
                <span>Choose a PCB image to begin</span>
              </div>
            )}
          </div>

          <div className="image-card">
            <h3>YOLO Detection Result</h3>

            {resultImage ? (
              <img
                src={resultImage}
                alt="PCB image with detected object boxes"
                className="pcb-image"
              />
            ) : (
              <div className="image-placeholder">
                <span>
                  The annotated image will appear here
                </span>
              </div>
            )}
          </div>
        </div>

        <button
          className="detect-button"
          onClick={detectObjects}
          disabled={!file || loading || !apiOnline}
          type="button"
        >
          {loading
            ? "Detecting..."
            : apiOnline
              ? "Detect PCB Objects"
              : "Waiting for YOLO API"}
        </button>

        {!apiOnline && (
          <div className="alert error">
            The backend is offline or the YOLO model failed to load.
            Start FastAPI and check http://127.0.0.1:8000/.
          </div>
        )}

        {error && <div className="alert error">{error}</div>}
        {message && <div className="alert success">{message}</div>}

        {detections.length > 0 && (
          <div className="results">
            <h3>Detected Objects ({detections.length})</h3>

            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Detected Class</th>
                    <th>Confidence</th>
                    <th>Bounding Box (x1, y1, x2, y2)</th>
                  </tr>
                </thead>

                <tbody>
                  {detections.map((item, index) => (
                    <tr key={`${item.class_id}-${index}`}>
                      <td>{index + 1}</td>
                      <td>{item.class_name}</td>
                      <td>
                        {(
                          (item.confidence_percent ??
                            item.confidence * 100)
                        ).toFixed(1)}
                        %
                      </td>
                      <td>{item.box.map((n) => Math.round(n)).join(", ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="subtitle">
              Confidence indicates the model's score, not proof that a
              component is faulty.
            </p>
          </div>
        )}
      </section>

      <section className="panel sensor-panel">
        <div className="section-heading">
          <div>
            <h2>Electrical Measurements</h2>
            <p>Independent live sensor readings from the backend.</p>
          </div>

          <span
            className={
              readings.connected
                ? "connection connected"
                : "connection disconnected"
            }
          >
            {readings.connected ? "Connected" : "Offline"}
          </span>
        </div>

        <div className="sensor-grid">
          <SensorCard label="Input Voltage" value={readings.vin} unit="V" />
          <SensorCard label="Output Voltage" value={readings.vout} unit="V" />
          <SensorCard label="Current" value={readings.current} unit="A" />
        </div>

        <button
          className="secondary-button"
          onClick={fetchReadings}
          type="button"
        >
          Refresh Readings
        </button>
      </section>

      <footer>PCB Inspection System · YOLO + FastAPI</footer>
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
