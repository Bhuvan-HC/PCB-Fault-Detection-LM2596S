
import { useState } from 'react'
import './App.css'

function App() {
  const [image, setImage] = useState(null)
  const [preview, setPreview] = useState(null)
  const [imageMessage, setImageMessage] = useState('')
  const [vin, setVin] = useState('')
  const [vout, setVout] = useState('')
  const [current, setCurrent] = useState('')
  const [result, setResult] = useState(null)

  function handleImageUpload(event) {
    const file = event.target.files?.[0]
    if (!file) return

    if (preview) URL.revokeObjectURL(preview)

    setImage(file)
    setPreview(URL.createObjectURL(file))
    setImageMessage('')
  }

  function processImage() {
    if (!image) {
      setImageMessage('Please upload a PCB image first.')
      return
    }

    setImageMessage(
      'Image uploaded. YOLO detection will be available after model integration.'
    )
  }

  function startTest() {
    if (vin === '' || vout === '' || current === '') {
      setResult({
        status: 'INCOMPLETE',
        message: 'Enter all three electrical readings.',
      })
      return
    }

    setResult({
      status: 'READY',
      message: 'Readings captured. ML prediction will be available after model integration.',
    })
  }

  return (
    <main className="dashboard">
      <header className="header">
        <div className="logo">PCB</div>
        <div>
          <h1>PCB Fault Detection</h1>
          <p>LM2596S Buck Converter Testing System</p>
        </div>
        <span className="connection">Software Preview</span>
      </header>

      <section className="welcome">
        <p className="eyebrow">PCB DIAGNOSTICS</p>
        <h2>Test your PCB with confidence.</h2>
        <p>
          Inspect visible damage using images or test electrical
          readings using the independent ML module.
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
              <img className="pcb-preview" src={preview} alt="Uploaded PCB" />
            ) : (
              <>
                <span className="upload-icon">↑</span>
                <strong>Upload PCB Image</strong>
                <span>Choose a JPG, PNG or other image file</span>
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

          {imageMessage && (
            <p className="message">{imageMessage}</p>
          )}

          <p className="hint">
            Detected locations will appear here after YOLO is integrated.
          </p>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <span className="number">02</span>
            <div>
              <h2>Electrical Testing</h2>
              <p>Random Forest ML</p>
            </div>
          </div>

          <p className="section-description">
            Enter readings from your LM2596S test PCB.
          </p>

          <label className="field">
            Input Voltage <span>(V)</span>
            <input
              type="number"
              step="any"
              min="0"
              placeholder="e.g. 12.0"
              value={vin}
              onChange={(e) => setVin(e.target.value)}
            />
          </label>

          <label className="field">
            Output Voltage <span>(V)</span>
            <input
              type="number"
              step="any"
              min="0"
              placeholder="e.g. 5.0"
              value={vout}
              onChange={(e) => setVout(e.target.value)}
            />
          </label>

          <label className="field">
            Output Current <span>(A)</span>
            <input
              type="number"
              step="any"
              min="0"
              placeholder="e.g. 0.5"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
            />
          </label>

          <button className="primary-button" onClick={startTest}>
            Start Test
          </button>

          <p className="hint">
            ML prediction will activate after the backend and trained model
            are connected. Manual readings do not represent live sensors.
          </p>
        </section>
      </div>

      <section className="result-panel">
        <div>
          <p className="eyebrow">TEST SUMMARY</p>
          <h2>Test Result</h2>
          <p>
            Image analysis and electrical testing operate independently.
          </p>
        </div>

        <div className="result-status">
          <span className="status-dot" />
          <strong>
            {result?.status ?? 'WAITING'}
          </strong>
          {result && <p>{result.message}</p>}
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
