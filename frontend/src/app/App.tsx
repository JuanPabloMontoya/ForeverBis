import { useEffect, useState } from 'react'
import { fetchHealth, type HealthResponse } from '../api/health'
import LevelSlider from '../features/planner/LevelSlider'

type ConnectionState =
  | { status: 'loading' }
  | { status: 'connected'; health: HealthResponse }
  | { status: 'error'; message: string }

const equipmentSlots = [
  'Head',
  'Neck',
  'Shoulders',
  'Back',
  'Chest',
  'Wrist',
  'Hands',
  'Waist',
  'Legs',
  'Feet',
  'Finger 1',
  'Finger 2',
  'Trinket 1',
  'Trinket 2',
  'Main hand',
  'Off hand',
  'Ranged',
]

function BackendStatus({ connection }: { connection: ConnectionState }) {
  if (connection.status === 'loading') {
    return (
      <div className="connection-pill" role="status" aria-label="Backend connection loading">
        <span className="status-dot status-pending" />
        Connecting to backend…
      </div>
    )
  }

  if (connection.status === 'error') {
    return (
      <div className="connection-pill connection-error" role="alert">
        <span className="status-dot status-error" />
        Backend unavailable
        <span className="connection-detail">{connection.message}</span>
      </div>
    )
  }

  const databaseUnavailable = connection.health.database !== 'healthy'
  return (
    <div
      className={`connection-pill ${databaseUnavailable ? 'connection-warning' : ''}`}
      role="status"
      aria-label={`Backend connected, database ${connection.health.database}`}
    >
      <span className={`status-dot ${databaseUnavailable ? 'status-pending' : 'status-good'}`} />
      Backend connected
      <span className="connection-detail">
        Database {databaseUnavailable ? 'unavailable' : 'healthy'}
      </span>
    </div>
  )
}

function PlaceholderSelect({ label }: { label: string }) {
  return (
    <label className="filter-field">
      <span>{label}</span>
      <select aria-label={label} disabled value="">
        <option value="">Available in a later phase</option>
      </select>
    </label>
  )
}

export default function App() {
  const [level, setLevel] = useState(1)
  const [connection, setConnection] = useState<ConnectionState>({ status: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    fetchHealth(controller.signal)
      .then((health) => setConnection({ status: 'connected', health }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        const message = error instanceof Error ? error.message : 'Could not reach the API.'
        setConnection({ status: 'error', message })
      })
    return () => controller.abort()
  }, [])

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="/" aria-label="Forever BIS home">
          <span className="brand-mark" aria-hidden="true">FB</span>
          <span className="brand-copy">
            <strong>Forever BIS</strong>
            <small>Gear progression planner</small>
          </span>
        </a>
        <nav className="header-nav" aria-label="Main navigation">
          <a className="nav-active" href="#planner">Planner</a>
          <a href="#about">About</a>
        </nav>
        <BackendStatus connection={connection} />
      </header>

      <main id="planner" className="main-content">
        <section className="hero-panel">
          <div className="hero-copy">
            <p className="eyebrow">World of Warcraft: Forever</p>
            <h1>Plan your journey to <span>best in slot.</span></h1>
            <p className="hero-description">
              A level-by-level gear planner is taking shape. This foundation contains no item
              recommendations or game data yet.
            </p>
          </div>
          <div className="hero-emblem" aria-hidden="true">
            <div className="emblem-ring"><span>FB</span></div>
          </div>
        </section>

        <section className="planner-card" aria-labelledby="planner-heading">
          <div className="section-title-row">
            <div>
              <p className="eyebrow">Character setup</p>
              <h2 id="planner-heading">Build your planner</h2>
            </div>
            <span className="phase-badge">Foundation</span>
          </div>

          <div className="filter-grid">
            <PlaceholderSelect label="Class" />
            <PlaceholderSelect label="Specialization" />
            <PlaceholderSelect label="Faction" />
          </div>

          <LevelSlider value={level} onChange={setLevel} />
        </section>

        <section className="equipment-section" aria-labelledby="equipment-heading">
          <div className="section-title-row equipment-title-row">
            <div>
              <p className="eyebrow">Equipment overview</p>
              <h2 id="equipment-heading">Gear slots</h2>
            </div>
            <span className="muted-caption">17 slots · Level {level}</span>
          </div>

          <div className="equipment-grid">
            {equipmentSlots.map((slot, index) => (
              <div className="equipment-slot" key={slot} aria-label={`${slot} slot empty`}>
                <span className="slot-mark" aria-hidden="true">{String(index + 1).padStart(2, '0')}</span>
                <span className="slot-name">{slot}</span>
                <span className="slot-empty">No item data</span>
              </div>
            ))}
          </div>
          <div className="empty-state" role="status">
            <span className="empty-state-icon" aria-hidden="true">✦</span>
            <div>
              <h3>Equipment data is not connected yet</h3>
              <p>
                The catalog and recommendation workflow will be added in later phases. No item
                names, stats, or sources are being shown here.
              </p>
            </div>
          </div>
        </section>

        <footer id="about" className="page-footer">
          <span>Forever BIS</span>
          <span>Community project · Not affiliated with Blizzard Entertainment</span>
        </footer>
      </main>
    </div>
  )
}
