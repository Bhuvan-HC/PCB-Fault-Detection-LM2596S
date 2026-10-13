
import { useEffect, useState } from 'react'
import './App.css'

const API_URL = 'http://localhost:8000'

function App() {
  const [image, setImage] = useState(null)
  const [preview, setPreview] = useState(null)
  const [imageMessage, setImageMessage] = useState('')
  const [readings, setReadings] = useState(null)
  const [connection, setConnection] = useState('Connecting...')
  const [testMessage, setTestMessage] = useState('')

  async function fetchReadings() {
    try {
      const response = await fetch(`${API_URL}/api/readings`)
      if (!response.ok) throw new Error('API unavailable')

      const data = await response.json()
      setReadings(data)
      setConnection(data.connected ? 'Connected' : 'Waiting for ESP32')
    } catch {
      setConnection('Backend offline')
    }
  }

  useEffect(() => {
    fetchReadings()
    const timer = setInterval(fetchReadings, 2000)
    return () => clearInterval(timer)
  }, [])

  function handleImageUpload(event) {
    const file = event.target.files?.[0]
    if (!file) return

    if (preview) URL.revokeObjectURL(preview)

    setImage(file)
    setPreview(URL.createObjectURL(file))
    setImageMessage('')
  }

  
async function processImage() {
  if (!image) {
    setImageMessage('Please upload a PCB image first.')
    return
  }

  setImageMessage('Uploading image...')

  try {
    const formData = new FormData()
    formData.append('file', image)

    const response = await fetch(
      `${API_URL}/api/process-image`,
      {
        method: 'POST',
        body: formData,
      }
    )

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || 'Image processing failed.')
    }

    setImageMessage(data.message)
  } catch (error) {
    setImageMessage(
      error.message || 'Could not connect to the backend.'
    )
  }
}


  async function startTest() {
    await fetchReadings()

    if (!readings?.connected) {
      setTestMessage('Waiting for electrical readings from the ESP32.')
      return
    }

    setTestMessage(
      'Readings received. Random Forest prediction will be enabled after model integration.'
    )
  }

  const hasReadings =
    readings?.connected &&
    readings.vin !== null &&
    readings.vout !== null &&
    readings.current !== null

  return (
    <main className="dashboard">
      <header className="header">
        <div className="logo">PCB</div>
        <div>
          <h1>PCB Fault Detection</h1>
          <p>LM2596S Buck Converter Testing System</p>
        </div>
        <span className="connection">{connection}</span>
      </header>

      <section className="welcome">
        <p className="eyebrow">PCB DIAGNOSTICS</p>
        <h2>Test your PCB with confidence.</h2>
        <p>
          Inspect visible damage or test electrical readings
          using the independent modules.
        </p>
      </section>

      <div className="modules">
        <section className="panel">
          <div className="panel-heading">
            <span className="number">01</span>
            <div>
              <h2>Image Processing</h2>
              <p>YOLO + OpenCV</p>
            </div>
          </div>

          <label className="upload-area">
            {preview ? (
              <img
                className="pcb-preview"
                src={preview}
                alt="Uploaded PCB"
              />
            ) : (
              <>
                <span className="upload-icon">↑</span>
                <strong>Upload PCB Image</strong>
                <span>Choose an image file</span>
              </>
            )}
            <input
              type="file"
              accept="image/*"
              onChange={handleImageUpload}
            />
          </label>

          <button className="primary-button" onClick={processImage}>
            Process Image
          </button>

          {imageMessage && <p className="message">{imageMessage}</p>}

          <p className="hint">
            YOLO detection will be connected separately.
          </p>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <span className="number">02</span>
            <div>
              <h2>Electrical Testing</h2>
              <p>ESP32 + INA219 + ADS1115</p>
            </div>
          </div>

          <div className="reading-card">
            <span>Input Voltage</span>
            <strong>
              {readings?.vin != null
                ? `${Number(readings.vin).toFixed(2)} V`
                : '-- V'}
            </strong>
          </div>

          <div className="reading-card">
            <span>Output Voltage</span>
            <strong>
              {readings?.vout != null
                ? `${Number(readings.vout).toFixed(2)} V`
                : '-- V'}
            </strong>
          </div>

          <div className="reading-card">
            <span>Output Current</span>
            <strong>
              {readings?.current != null
                ? `${Number(readings.current).toFixed(3)} A`
                : '-- A'}
            </strong>
          </div>

          <button className="primary-button" onClick={startTest}>
            Start Test
          </button>

          <p className="hint">
            Readings refresh automatically every 2 seconds.
          </p>

          {testMessage && <p className="message">{testMessage}</p>}
        </section>
      </div>

      <section className="result-panel">
        <div>
          <p className="eyebrow">TEST SUMMARY</p>
          <h2>Test Result</h2>
          <p>Electrical testing and image processing are independent.</p>
        </div>

        <div className="result-status">
          <span className="status-dot" />
          <strong>{hasReadings ? 'READINGS AVAILABLE' : 'WAITING'}</strong>
          <p>
            {hasReadings
              ? 'Electrical readings received. ML prediction is not connected yet.'
              : 'Waiting for valid electrical readings.'}
          </p>
        </div>
      </section>

      <footer>
        LM2596S PCB Fault Detection System
        <span>YOLO + OpenCV · Random Forest</span>
      </footer>
    </main>
  )
}

export default App
