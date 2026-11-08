import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { fetchItem, fetchItems, type CatalogItem } from '../../api/catalog'
import {
  fetchGearPlan,
  fetchScoringProfiles,
  type GearPlan,
  type PlannerCandidate,
  type PlannerSlot,
  type ScoringProfile,
  submitItemSuggestion,
} from '../../api/planner'

type RequestState = 'loading' | 'ready' | 'error'
export type PlannerNavigation = (page: 'planner' | 'catalog') => void
type SlotDefinition = { id: string; name: string; mark: string }

const LEFT_SLOTS: SlotDefinition[] = [
  { id: 'head', name: 'Head', mark: 'HD' },
  { id: 'neck', name: 'Neck', mark: 'NK' },
  { id: 'shoulders', name: 'Shoulders', mark: 'SH' },
  { id: 'back', name: 'Back', mark: 'BK' },
  { id: 'chest', name: 'Chest', mark: 'CH' },
  { id: 'wrist', name: 'Wrist', mark: 'WR' },
  { id: 'hands', name: 'Hands', mark: 'HN' },
  { id: 'waist', name: 'Waist', mark: 'WA' },
  { id: 'legs', name: 'Legs', mark: 'LG' },
  { id: 'feet', name: 'Feet', mark: 'FT' },
]

const RIGHT_SLOTS: SlotDefinition[] = [
  { id: 'ring_1', name: 'Ring 1', mark: 'R1' },
  { id: 'ring_2', name: 'Ring 2', mark: 'R2' },
  { id: 'trinket_1', name: 'Trinket 1', mark: 'T1' },
  { id: 'trinket_2', name: 'Trinket 2', mark: 'T2' },
  { id: 'main_hand', name: 'Main Hand', mark: 'MH' },
  { id: 'off_hand', name: 'Off Hand', mark: 'OH' },
  { id: 'ranged', name: 'Ranged', mark: 'RG' },
]

function qualityClass(quality: string | null) {
  const known = ['poor', 'common', 'uncommon', 'rare', 'epic', 'legendary', 'artifact']
  return quality && known.includes(quality.toLowerCase())
    ? `quality-${quality.toLowerCase()}`
    : 'quality-unknown'
}

function profileMap(profiles: ScoringProfile[]) {
  return profiles.reduce<Record<string, ScoringProfile[]>>((map, profile) => {
    map[profile.class_name] ??= []
    map[profile.class_name].push(profile)
    return map
  }, {})
}

function LevelProgression({
  level,
  onChange,
  loading,
}: {
  level: number
  onChange: (level: number) => void
  loading: boolean
}) {
  const selectedButton = useRef<HTMLButtonElement | null>(null)
  const levels = Array.from({ length: 60 }, (_, index) => index + 1)

  useEffect(() => {
    selectedButton.current?.scrollIntoView?.({ behavior: 'smooth', block: 'nearest', inline: 'center' })
  }, [level])

  function moveTo(next: number) {
    const bounded = Math.min(60, Math.max(1, next))
    onChange(bounded)
    requestAnimationFrame(() => document.getElementById(`level-${bounded}`)?.focus())
  }

  return (
    <section className="level-progression" aria-labelledby="level-heading">
      <div className="level-heading-row">
        <div><p className="eyebrow">Your journey</p><h2 id="level-heading">Level progression</h2></div>
        <div className="level-current" aria-live="polite"><span>LEVEL</span><strong>{level}</strong></div>
      </div>
      <div className="level-controls">
        <button type="button" className="level-control" disabled={level === 1} onClick={() => moveTo(level - 1)} aria-label="Previous level">‹</button>
        <div className="level-track-shell">
          <span className="level-boundary">1</span>
          <div className="level-track" role="group" aria-label="Choose a character level">
            {levels.map((value) => (
              <button
                key={value}
                id={`level-${value}`}
                ref={value === level ? selectedButton : null}
                type="button"
                className={`level-step${value === level ? ' is-selected' : ''}`}
                aria-label={`Level ${value}`}
                aria-pressed={value === level}
                onClick={() => onChange(value)}
                onKeyDown={(event) => {
                  if (event.key === 'ArrowRight') { event.preventDefault(); moveTo(value + 1) }
                  if (event.key === 'ArrowLeft') { event.preventDefault(); moveTo(value - 1) }
                  if (event.key === 'Home') { event.preventDefault(); moveTo(1) }
                  if (event.key === 'End') { event.preventDefault(); moveTo(60) }
                }}
              >{value}</button>
            ))}
          </div>
          <span className="level-boundary">60</span>
        </div>
        <button type="button" className="level-control" disabled={level === 60} onClick={() => moveTo(level + 1)} aria-label="Next level">›</button>
      </div>
      <p className="level-progress-note" aria-live="polite">
        {loading ? 'Refreshing gear for this character and level…' : 'Every level refreshes eligibility and item scores from the planner API.'}
      </p>
    </section>
  )
}

function EquipmentSlot({
  slot,
  result,
  busy,
  onSelect,
}: {
  slot: SlotDefinition
  result?: PlannerSlot
  busy: boolean
  onSelect: (slot: SlotDefinition) => void
}) {
  const candidate = result?.recommendation
  const status = busy
    ? 'Updating recommendations'
    : result?.status === 'recommended'
      ? 'Verified recommendation'
      : result?.status === 'insufficient_data'
        ? 'Insufficient verified data'
        : 'No recommendation available'
  return (
    <button
      className={`paperdoll-slot ${candidate ? 'paperdoll-slot-recommended' : ''}`}
      type="button"
      aria-label={`${slot.name}: ${candidate ? candidate.item.name : status}`}
      onClick={() => onSelect(slot)}
    >
      {candidate?.item.icon_url ? (
        <img className={`paperdoll-slot-mark item-slot-icon ${qualityClass(candidate.item.quality)}`} src={candidate.item.icon_url} alt="" loading="lazy" />
      ) : (
        <span className="paperdoll-slot-mark" aria-hidden="true">{slot.mark}</span>
      )}
      <span className="paperdoll-slot-copy">
        <strong>{slot.name}</strong>
        <small>{candidate ? candidate.item.name : busy ? 'Refreshing…' : status}</small>
        {candidate && <small>{candidate.item.quality ?? 'Quality unknown'} · Req. level {candidate.item.required_level ?? 'unknown'}</small>}
      </span>
      {candidate?.result.score !== null && candidate?.result.score !== undefined ? (
        <span className="slot-score">{candidate.result.score}</span>
      ) : <span className="slot-unavailable" aria-hidden="true">{candidate ? '✓' : '—'}</span>}
    </button>
  )
}

function ItemDetailPanel({
  item,
  candidate,
  onClose,
}: {
  item: CatalogItem
  candidate: PlannerCandidate | null
  onClose: () => void
}) {
  return (
    <div className="detail-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="item-detail-panel planner-item-detail" role="dialog" aria-modal="true" aria-labelledby="planner-item-heading">
        <button className="detail-close" type="button" onClick={onClose} aria-label="Close item details">×</button>
        <p className="eyebrow">Forever item · provider ID {item.source_item_id}</p>
        <div className="detail-title-row">
          {item.icon_url && <img className="detail-icon" src={item.icon_url} alt="" />}
          <div>
            <span className={`item-quality ${qualityClass(item.quality)}`}>{item.quality ?? 'Quality unknown'}</span>
            <h2 id="planner-item-heading">{item.name}</h2>
            <p className="muted-caption">{item.verification_status} · {item.game_version.build ?? 'Build unknown'}</p>
          </div>
        </div>
        <dl className="detail-facts">
          <div><dt>Required level</dt><dd>{item.required_level ?? 'Unknown'}</dd></div>
          <div><dt>Item level</dt><dd>{item.item_level ?? 'Unknown'}</dd></div>
          <div><dt>Slot</dt><dd>{item.inventory_type ?? 'Unknown'}</dd></div>
          <div><dt>Availability</dt><dd>{item.availability_status}</dd></div>
          {item.armor_value !== null && <div><dt>Armor</dt><dd>{item.armor_value}</dd></div>}
          {item.weapon_damage_min !== null && item.weapon_damage_max !== null && <div><dt>Weapon damage</dt><dd>{item.weapon_damage_min}–{item.weapon_damage_max}</dd></div>}
          {item.weapon_speed !== null && <div><dt>Weapon speed</dt><dd>{item.weapon_speed}</dd></div>}
        </dl>
        {candidate && (
          <section className="detail-subsection planner-score-detail">
            <h3>Score explanation</h3>
            <p><strong>Score {candidate.result.score}</strong> · Eligibility: {candidate.result.eligibility.status} · Profile {candidate.result.profile_version}</p>
            {candidate.result.contributions.length > 0 ? (
              <ul>{candidate.result.contributions.map((part) => <li key={part.stat_type}>{part.stat_type}: {part.value} × {part.weight} = {part.contribution}</li>)}</ul>
            ) : <p>No statistic contributions were returned.</p>}
            <p>Item score is not a complete equipment-set optimization.</p>
          </section>
        )}
        <section className="detail-subsection"><h3>Statistics</h3>
          {item.stats.length ? <ul>{item.stats.map((stat, index) => <li key={`${stat.stat_type}-${index}`}>{stat.stat_type}: {stat.value}</li>)}</ul> : <p>Statistics unavailable or completeness not verified.</p>}
        </section>
        <section className="detail-subsection"><h3>Effects</h3>
          {item.effects.length ? <ul>{item.effects.map((effect, index) => <li key={`${effect.effect_type}-${index}`}>{effect.description ?? effect.effect_type}</li>)}</ul> : <p>Effect data unavailable or completeness not verified.</p>}
        </section>
        <section className="detail-subsection"><h3>Restrictions and eligibility</h3>
          <p>Eligibility verification: {item.eligibility_status}</p>
          {item.restrictions.length ? <ul>{item.restrictions.map((restriction, index) => <li key={`${restriction.restriction_type}-${index}`}>{restriction.restriction_type}: {restriction.restriction_value} · {restriction.verification_status}</li>)}</ul> : <p>No restrictions are recorded; unrestricted use is not established.</p>}
        </section>
        <section className="detail-subsection"><h3>Acquisition</h3>
          {item.acquisitions.length ? <ul>{item.acquisitions.map((entry, index) => <li key={`${entry.acquisition_source.source_type}-${index}`}>{entry.acquisition_source.source_type}: {entry.acquisition_source.name ?? 'Name unknown'} · {entry.verification_status}</li>)}</ul> : <p>Acquisition source is not verified in the catalog.</p>}
          <p>Next upgrade is not established by the available data.</p>
        </section>
        <div className="detail-attribution">
          <a href={item.source_item_url ?? item.source.base_url} target="_blank" rel="noreferrer">{item.source.attribution_text}</a>
          {item.wowhead_url && item.verification_status === 'verified' && <a className="wowhead-link" href={item.wowhead_url} target="_blank" rel="noreferrer">Open verified Wowhead Forever page ↗</a>}
        </div>
      </section>
    </div>
  )
}

function recommendationLabel(slot?: PlannerSlot) {
  if (!slot) return 'Recommendation data is loading.'
  if (slot.status === 'unavailable') return 'No verified recommendation is available for this slot and level.'
  if (slot.status === 'insufficient_data') return slot.explanation.join(' ')
  return 'A verified candidate was scored by the backend for this slot. This is an individual item comparison, not a full-set optimum.'
}

export default function GearPlanner({ onNavigate }: { onNavigate: PlannerNavigation }) {
  const [profiles, setProfiles] = useState<ScoringProfile[]>([])
  const [profileState, setProfileState] = useState<RequestState>('loading')
  const [profileError, setProfileError] = useState<string | null>(null)
  const [characterClass, setCharacterClass] = useState('Warrior')
  const [specialization, setSpecialization] = useState('Arms')
  const [faction, setFaction] = useState<'Alliance' | 'Horde'>('Alliance')
  const [level, setLevel] = useState(1)
  const [plan, setPlan] = useState<GearPlan | null>(null)
  const [planState, setPlanState] = useState<RequestState>('loading')
  const [planError, setPlanError] = useState<string | null>(null)
  const [activeSlot, setActiveSlot] = useState<SlotDefinition | null>(null)
  const [catalogRecords, setCatalogRecords] = useState<CatalogItem[]>([])
  const [catalogState, setCatalogState] = useState<RequestState>('ready')
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [selectedItem, setSelectedItem] = useState<CatalogItem | null>(null)
  const [selectedCandidate, setSelectedCandidate] = useState<PlannerCandidate | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetchScoringProfiles(controller.signal)
      .then((rows) => { setProfiles(rows); setProfileState('ready'); setProfileError(null) })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return
        setProfileError(reason instanceof Error ? reason.message : 'Scoring profiles could not be loaded.')
        setProfileState('error')
      })
    return () => controller.abort()
  }, [])

  const classes = useMemo(() => profileMap(profiles), [profiles])
  const classNames = useMemo(() => Object.keys(classes).sort(), [classes])
  const specializations = classes[characterClass]?.map((profile) => profile.specialization) ?? []
  const activeProfile = profiles.find((profile) =>
    profile.class_name === characterClass && profile.specialization === specialization,
  )

  useEffect(() => {
    if (!classNames.length) return
    if (!classes[characterClass]) {
      const firstClass = classNames[0]
      setCharacterClass(firstClass)
      setSpecialization(classes[firstClass][0].specialization)
      return
    }
    if (!specializations.includes(specialization)) setSpecialization(specializations[0] ?? '')
  }, [classNames, classes, characterClass, specialization, specializations])

  useEffect(() => {
    if (profileState !== 'ready' || !activeProfile) return
    const controller = new AbortController()
    setPlan(null)
    setPlanState('loading')
    setPlanError(null)
    fetchGearPlan({ class_name: characterClass, specialization, faction, level }, controller.signal)
      .then((result) => { setPlan(result); setPlanState('ready') })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return
        setPlanError(reason instanceof Error ? reason.message : 'Gear recommendations could not be loaded.')
        setPlanState('error')
      })
    return () => controller.abort()
  }, [activeProfile, characterClass, faction, level, profileState, specialization])

  useEffect(() => {
    if (!activeSlot) return
    const controller = new AbortController()
    setCatalogState('loading')
    setCatalogRecords([])
    setCatalogError(null)
    const inventoryType = activeSlot.id.startsWith('ring_')
      ? 'Finger'
      : activeSlot.id.startsWith('trinket_')
        ? 'Trinket'
        : activeSlot.name
    fetchItems({ inventory_type: inventoryType, page: 1, page_size: 24, sort_by: 'name' }, controller.signal)
      .then((page) => { setCatalogRecords(page.items); setCatalogState('ready') })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return
        setCatalogError(reason instanceof Error ? reason.message : 'Catalog records could not be loaded.')
        setCatalogState('error')
      })
    return () => controller.abort()
  }, [activeSlot])

  useEffect(() => {
    if (selectedId === null) return
    const controller = new AbortController()
    setSelectedItem(null)
    setDetailLoading(true)
    setDetailError(null)
    fetchItem(selectedId, controller.signal)
      .then(setSelectedItem)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setDetailError(reason instanceof Error ? reason.message : 'Item details unavailable.')
      })
      .finally(() => { if (!controller.signal.aborted) setDetailLoading(false) })
    return () => controller.abort()
  }, [selectedId])

  function changeClass(nextClass: string) {
    setCharacterClass(nextClass)
    setSpecialization(classes[nextClass]?.[0]?.specialization ?? '')
  }

  function openCandidate(candidate: PlannerCandidate) {
    setSelectedCandidate(candidate)
    setSelectedId(candidate.item.id)
  }

  function closeItem() {
    setSelectedId(null)
    setSelectedItem(null)
    setSelectedCandidate(null)
  }

  const slotsByName = new Map((plan?.slots ?? []).map((slot) => [slot.slot, slot]))
  const activeSlotResult = activeSlot ? slotsByName.get(activeSlot.name) : undefined

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="#planner" aria-label="Forever BIS home">
          <span className="brand-mark" aria-hidden="true">FB</span>
          <span className="brand-copy"><strong>Forever BIS</strong><small>Level-by-level gear planner</small></span>
        </a>
        <nav className="header-nav" aria-label="Main navigation">
          <button className="nav-active" type="button" aria-current="page">Gear Planner</button>
          <button type="button" onClick={() => onNavigate('catalog')}>Item Database</button>
        </nav>
        <span className="planner-status-pill"><span className={`status-dot ${planState === 'ready' ? 'status-good' : planState === 'error' ? 'status-error' : 'status-pending'}`} />
          {planState === 'ready' ? 'Planner connected' : planState === 'error' ? 'Planner unavailable' : 'Loading planner'}
        </span>
      </header>

      <main id="planner" className="main-content planner-page">
        <section className="planner-hero">
          <div>
            <p className="eyebrow">World of Warcraft: Forever</p>
            <h1>Gear for every <span>step of the journey.</span></h1>
            <p>Choose your character and level. Slot results come from backend eligibility and scoring; incomplete evidence stays visible.</p>
          </div>
          <div className="planner-crest" aria-hidden="true"><span>FB</span></div>
        </section>

        {profileState === 'error' && <div className="planner-alert" role="alert">Scoring profiles could not be loaded: {profileError}</div>}
        <section className="planner-config" aria-label="Character configuration">
          <label className="planner-field"><span>Class</span><select aria-label="Class" value={characterClass} disabled={profileState !== 'ready' || !classNames.length} onChange={(event) => changeClass(event.target.value)}>
            {classNames.map((name) => <option key={name} value={name}>{name}</option>)}
          </select></label>
          <label className="planner-field"><span>Specialization</span><select aria-label="Specialization" value={specialization} disabled={profileState !== 'ready' || !specializations.length} onChange={(event) => setSpecialization(event.target.value)}>
            {specializations.map((name) => <option key={name} value={name}>{name}</option>)}
          </select></label>
          <label className="planner-field"><span>Faction</span><select aria-label="Faction" value={faction} onChange={(event) => setFaction(event.target.value as 'Alliance' | 'Horde')}>
            <option value="Alliance">Alliance</option><option value="Horde">Horde</option>
          </select></label>
          <div className="character-context" aria-live="polite"><span>Planning for</span><strong>{characterClass || 'Select a class'} · {specialization || 'Select a specialization'}</strong><small>{faction} · Level {level}</small></div>
          {activeProfile && <p className={`profile-readiness ${activeProfile.provisional || !Object.keys(activeProfile.stat_weights).length ? 'is-provisional' : 'is-configured'}`}>
            {Object.keys(activeProfile.stat_weights).length === 0
              ? 'Scoring profile not configured — no validated weights are available.'
              : activeProfile.provisional
                ? `Provisional scoring profile ${activeProfile.version}; scores are not recommendations.`
                : `Scoring profile ${activeProfile.version}`}
          </p>}
        </section>

        <LevelProgression level={level} onChange={setLevel} loading={planState === 'loading'} />

        {planState === 'error' && <div className="planner-alert" role="alert"><strong>Planner data unavailable.</strong> {planError}</div>}
        {planState === 'loading' && <div className="planner-loading" role="status">Updating slot eligibility and scores for level {level}…</div>}

        <section className="paperdoll-panel" aria-labelledby="equipment-heading" aria-busy={planState === 'loading'}>
          <div className="paperdoll-heading">
            <div><p className="eyebrow">Character equipment</p><h2 id="equipment-heading">Your gear at level {level}</h2></div>
            <span className="unavailable-legend">Backend-scored individual items · no full-set optimization</span>
          </div>
          <div className="paperdoll-layout">
            <div className="slot-group slot-group-left" aria-label="Armor slots">
              {LEFT_SLOTS.map((slot) => <EquipmentSlot key={slot.id} slot={slot} result={slotsByName.get(slot.name)} busy={planState === 'loading'} onSelect={setActiveSlot} />)}
            </div>
            <div className="character-figure" aria-label={`Character preview: ${characterClass}`}>
              <div className="figure-halo" aria-hidden="true" />
              <div className="figure-silhouette" aria-hidden="true"><span className="figure-head" /><span className="figure-body" /><span className="figure-cape" /></div>
              <span className="figure-class">{characterClass}</span><span className="figure-level">Level {level}</span>
            </div>
            <div className="slot-group slot-group-right" aria-label="Jewelry and weapon slots">
              {RIGHT_SLOTS.map((slot) => <EquipmentSlot key={slot.id} slot={slot} result={slotsByName.get(slot.name)} busy={planState === 'loading'} onSelect={setActiveSlot} />)}
            </div>
          </div>
          {planState === 'ready' && plan && (
            <div className="plan-state-summary" role="status">
              {!plan.profile_configured
                ? 'No verified recommendations can be calculated: this specialization has no scoring weights configured.'
                : plan.profile_provisional
                  ? 'This scoring profile is provisional, so its scores are not presented as recommendations.'
                  : 'A slot score compares individual items only; it does not optimize a complete equipment set.'}
            </div>
          )}
        </section>

        <footer className="page-footer"><span>Forever BIS · Level progression planner</span><span>Only verified, eligible, scored records can be recommended</span></footer>
      </main>

      {activeSlot && (
        <div className="detail-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setActiveSlot(null)}>
          <section className="slot-record-panel planner-slot-panel" role="dialog" aria-modal="true" aria-labelledby="slot-record-heading">
            <button className="detail-close" type="button" aria-label="Close slot details" onClick={() => setActiveSlot(null)}>×</button>
            <p className="eyebrow">{characterClass} · {specialization} · {faction} · Level {level}</p>
            <h2 id="slot-record-heading">{activeSlot.name}</h2>
            <p className={`slot-result-status slot-result-${activeSlotResult?.status ?? 'unavailable'}`}>{recommendationLabel(activeSlotResult)}</p>
            {activeSlotResult?.recommendation && <CandidateCard label="Recommended item" candidate={activeSlotResult.recommendation} onOpen={openCandidate} />}
            {activeSlotResult?.alternatives.length ? <section className="planner-alternatives"><h3>Alternatives</h3>
              {activeSlotResult.alternatives.map((candidate) => <CandidateCard key={candidate.item.id} label="Alternative" candidate={candidate} onOpen={openCandidate} />)}
            </section> : null}
            {activeSlotResult && !activeSlotResult.alternatives.length && <p className="muted-caption">No verified, comparable alternatives are available.</p>}
            {activeSlotResult?.status !== 'recommended' && activeSlotResult?.explanation.map((reason, index) => <p className="planner-reason" key={`${reason}-${index}`}>{reason}</p>)}
            <section className="catalog-records-in-slot">
              <h3>Catalog records · not recommendations</h3>
              {catalogState === 'loading' && <p role="status">Loading provider records…</p>}
              {catalogState === 'error' && <p role="alert">{catalogError}</p>}
              {catalogState === 'ready' && catalogRecords.length === 0 && <p>No matching records are reported in the catalog. This does not prove no item exists for this slot.</p>}
              {catalogState === 'ready' && catalogRecords.map((item) => <button type="button" className="slot-record-card" key={item.id} onClick={() => { setSelectedCandidate(null); setSelectedId(item.id) }}>
                {item.icon_url ? <img src={item.icon_url} alt="" /> : <span className="slot-record-no-icon" aria-hidden="true">?</span>}
                <span><strong>{item.name}</strong><small>{item.quality ?? 'Quality unknown'} · {item.verification_status}</small></span>
              </button>)}
            </section>
            <SuggestionForm
              character={{ class_name: characterClass, specialization, faction, character_level: level }}
              slot={activeSlot.id}
            />
            <button className="secondary-button" type="button" onClick={() => onNavigate('catalog')}>Open Item Database</button>
          </section>
        </div>
      )}
      {selectedId !== null && detailLoading && <div className="detail-backdrop"><div className="catalog-state" role="status">Loading item details…</div></div>}
      {selectedId !== null && detailError && <div className="detail-backdrop" role="alert"><div className="catalog-state catalog-error"><p>{detailError}</p><button className="secondary-button" onClick={closeItem}>Close</button></div></div>}
      {selectedItem && <ItemDetailPanel item={selectedItem} candidate={selectedCandidate} onClose={closeItem} />}
    </div>
  )
}

function SuggestionForm({
  character,
  slot,
}: {
  character: { class_name: string; specialization: string; faction: 'Alliance' | 'Horde'; character_level: number }
  slot: string
}) {
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [explanation, setExplanation] = useState('')
  const [evidence, setEvidence] = useState('')
  const [state, setState] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')
  const [message, setMessage] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setState('sending')
    setMessage('')
    try {
      const receipt = await submitItemSuggestion({
        ...character,
        equipment_slot: slot,
        suggested_item_name: name.trim(),
        wowhead_url: url.trim(),
        explanation: explanation.trim() || undefined,
        supporting_evidence: evidence.trim() || undefined,
      })
      setState('sent')
      setMessage(`Suggestion ${receipt.id} was submitted for review${receipt.duplicate_flagged ? ' and flagged as a possible duplicate' : ''}.`)
    } catch (error) {
      setState('error')
      setMessage(error instanceof Error ? error.message : 'Suggestion submission failed.')
    }
  }

  if (state === 'sent') return <p className="suggestion-receipt" role="status">{message} Approval does not automatically verify the item.</p>
  return (
    <form className="suggestion-form" onSubmit={submit}>
      <h3>Suggest a better item</h3>
      <p>Suggestions are reviewed before they can affect catalog data or recommendations.</p>
      <label>Item name<input required maxLength={250} value={name} onChange={(event) => setName(event.target.value)} /></label>
      <label>Wowhead Forever item URL<input required type="url" placeholder="https://www.wowhead.com/forever/item=123/item-name" value={url} onChange={(event) => setUrl(event.target.value)} /></label>
      <label>Why is this a better option? (optional)<textarea maxLength={4000} value={explanation} onChange={(event) => setExplanation(event.target.value)} /></label>
      <label>Additional evidence (optional)<textarea maxLength={4000} value={evidence} onChange={(event) => setEvidence(event.target.value)} /></label>
      {state === 'error' && <p className="suggestion-error" role="alert">{message}</p>}
      <button className="secondary-button" type="submit" disabled={state === 'sending'}>{state === 'sending' ? 'Submitting…' : 'Submit for review'}</button>
    </form>
  )
}

function CandidateCard({
  label,
  candidate,
  onOpen,
}: {
  label: string
  candidate: PlannerCandidate
  onOpen: (candidate: PlannerCandidate) => void
}) {
  const item = candidate.item
  return (
    <article className="planner-candidate">
      <div className="planner-candidate-title">
        {item.icon_url ? <img src={item.icon_url} alt="" /> : <span className="slot-record-no-icon" aria-hidden="true">?</span>}
        <div><span className="candidate-label">{label}</span><strong className={qualityClass(item.quality)}>{item.name}</strong>
          <small>{item.quality ?? 'Quality unknown'} · Req. level {item.required_level ?? 'unknown'}</small></div>
        <strong className="candidate-score">{candidate.result.score}</strong>
      </div>
      {candidate.score_difference !== null && <p className="muted-caption">Score difference: {candidate.score_difference}</p>}
      <button type="button" className="text-button" onClick={() => onOpen(candidate)}>View item and score details</button>
    </article>
  )
}
