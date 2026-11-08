import { useEffect, useMemo, useRef, useState } from 'react'
import {
  fetchCatalogSummary,
  fetchItem,
  fetchItems,
  type CatalogItem,
  type CatalogSummary,
} from '../api/catalog'

type RequestState = 'loading' | 'ready' | 'error'

function qualityTone(quality: string | null): string {
  const known = ['poor', 'common', 'uncommon', 'rare', 'epic', 'legendary', 'artifact']
  return quality && known.includes(quality.toLowerCase())
    ? `quality-${quality.toLowerCase()}`
    : 'quality-unknown'
}

function qualityLabel(quality: string | null): string {
  return quality ? quality.charAt(0).toUpperCase() + quality.slice(1) : 'Quality unknown'
}

function verificationLabel(status: string): string {
  return status === 'needs_review' ? 'Needs review' : 'Provider reported'
}

function issueFor(item: CatalogItem, field: string) {
  return item.quality_issues.find((issue) => issue.field_name === field)
}

function RequiredLevel({ item }: { item: CatalogItem }) {
  const issue = issueFor(item, 'required_level')
  if (issue?.issue_code === 'list_detail_conflict') {
    const values = issue.observed_values as { list?: number | null; detail?: number | null } | null
    return <span>Required level under review · list {values?.list ?? 'unknown'} / detail {values?.detail ?? 'unknown'}</span>
  }
  return <span>Required level {item.required_level === null ? 'unknown' : item.required_level}</span>
}

function ItemCard({ item, onOpen }: { item: CatalogItem; onOpen: (item: CatalogItem) => void }) {
  return (
    <article className="catalog-item-card">
      <button
        className="item-card-open"
        type="button"
        onClick={() => onOpen(item)}
        aria-label={`View ${item.name} details`}
      >
        {item.icon_url ? (
          <img className="item-icon" src={item.icon_url} alt="" loading="lazy" />
        ) : (
          <span className="item-icon item-icon-missing" aria-label="No icon reported">?</span>
        )}
        <span className="item-card-main">
          <span className={`item-quality ${qualityTone(item.quality)}`}>{qualityLabel(item.quality)}</span>
          <strong className="item-name">{item.name}</strong>
          <span className="item-meta">
            {item.item_level === null ? 'Item level unknown' : `Item level ${item.item_level}`}
            <span aria-hidden="true"> · </span>
            {item.inventory_type ?? 'Slot unknown'}
          </span>
          <span className="item-meta"><RequiredLevel item={item} /></span>
        </span>
        <span className={`verification-badge ${item.verification_status === 'needs_review' ? 'needs-review' : ''}`}>
          {verificationLabel(item.verification_status)}
        </span>
      </button>
      <div className="item-card-footer">
        <span>Forever · {item.game_version.build ?? 'build unknown'}</span>
        <a href={item.source_item_url ?? item.source.base_url} target="_blank" rel="noreferrer">
          Data from TheWoWDB
        </a>
      </div>
    </article>
  )
}

function ItemDetail({ item, onClose }: { item: CatalogItem; onClose: () => void }) {
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [onClose])

  const statsUnverified = issueFor(item, 'stats')?.issue_code === 'empty_array_semantics_unverified'
  const restrictionsUnverified = issueFor(item, 'classes')?.issue_code === 'empty_array_semantics_unverified'
  const effectsUnverified = issueFor(item, 'effects')?.issue_code === 'empty_array_semantics_unverified'

  return (
    <div
      className="detail-backdrop"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <section className="item-detail-panel" role="dialog" aria-modal="true" aria-labelledby="item-detail-heading">
        <button className="detail-close" type="button" onClick={onClose} aria-label="Close item details">×</button>
        <p className="eyebrow">Forever item · source ID {item.source_item_id}</p>
        <div className="detail-title-row">
          {item.icon_url ? <img className="detail-icon" src={item.icon_url} alt="" /> : null}
          <div>
            <span className={`item-quality ${qualityTone(item.quality)}`}>{qualityLabel(item.quality)}</span>
            <h2 id="item-detail-heading">{item.name}</h2>
            <p className="muted-caption">
              {verificationLabel(item.verification_status)} · Build {item.game_version.build ?? 'unknown'}
            </p>
          </div>
        </div>

        <dl className="detail-facts">
          <div><dt>Item level</dt><dd>{item.item_level ?? 'Unknown'}</dd></div>
          <div><dt>Required level</dt><dd><RequiredLevel item={item} /></dd></div>
          <div><dt>Equipment slot</dt><dd>{item.inventory_type ?? 'Unknown'}</dd></div>
          <div><dt>Armor type</dt><dd>{item.armor_type ?? 'Unknown'}</dd></div>
          <div><dt>Weapon type</dt><dd>{item.weapon_type ?? 'Unknown'}</dd></div>
          <div><dt>Availability</dt><dd>{item.availability_status === 'unknown' ? 'Unknown' : item.availability_status}</dd></div>
        </dl>

        <section className="detail-subsection">
          <h3>Statistics</h3>
          {item.stats.length ? (
            <ul>{item.stats.map((stat, index) => <li key={`${stat.stat_type}-${index}`}>{stat.stat_type}: {stat.value}</li>)}</ul>
          ) : <p>{statsUnverified ? 'No stats reported; completeness is unverified.' : 'Statistics are unavailable.'}</p>}
        </section>
        <section className="detail-subsection">
          <h3>Effects</h3>
          {item.effects.length ? (
            <ul>{item.effects.map((effect, index) => <li key={`${effect.effect_type}-${index}`}>
              {effect.description ?? effect.effect_type}{effect.spell_id ? ` · Spell ${effect.spell_id}` : ''}
            </li>)}</ul>
          ) : <p>{effectsUnverified ? 'No effects reported; completeness is unverified.' : 'Effects are unavailable.'}</p>}
        </section>
        <section className="detail-subsection">
          <h3>Restrictions</h3>
          {item.restrictions.length ? (
            <ul>{item.restrictions.map((restriction, index) => <li key={`${restriction.restriction_type}-${index}`}>
              {restriction.restriction_type}: {restriction.restriction_value} · {verificationLabel(restriction.verification_status)}
            </li>)}</ul>
          ) : <p>{restrictionsUnverified ? 'No class restrictions reported; unrestricted use is not established.' : 'Restrictions are unavailable.'}</p>}
        </section>

        {item.quality_issues.length > 0 && (
          <section className="quality-issues" aria-labelledby="quality-issues-heading">
            <h3 id="quality-issues-heading">Data quality notes</h3>
            <ul>{item.quality_issues.map((issue, index) => <li key={`${issue.field_name}-${issue.issue_code}-${index}`}>
              <strong>{issue.field_name.replaceAll('_', ' ')}:</strong> {issue.message}
            </li>)}</ul>
          </section>
        )}

        <div className="detail-attribution">
          <span>Data captured {new Date(item.game_version.observed_at).toLocaleDateString()}</span>
          <a href={item.source_item_url ?? item.source.base_url} target="_blank" rel="noreferrer">
            {item.source.attribution_text}
          </a>
          {item.wowhead_url && (
            <a className="wowhead-link" href={item.wowhead_url} target="_blank" rel="noreferrer">
              Open verified Wowhead Forever page ↗
            </a>
          )}
        </div>
      </section>
    </div>
  )
}

function CatalogPage({ onNavigate }: { onNavigate: (page: 'planner' | 'catalog') => void }) {
  const [summary, setSummary] = useState<CatalogSummary | null>(null)
  const [items, setItems] = useState<CatalogItem[]>([])
  const [requestState, setRequestState] = useState<RequestState>('loading')
  const [summaryError, setSummaryError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [quality, setQuality] = useState('')
  const [inventoryType, setInventoryType] = useState('')
  const [source, setSource] = useState('')
  const [minLevel, setMinLevel] = useState('')
  const [maxLevel, setMaxLevel] = useState('')
  const [verification, setVerification] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [pages, setPages] = useState(0)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [selectedItem, setSelectedItem] = useState<CatalogItem | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search.trim()), 250)
    return () => window.clearTimeout(timer)
  }, [search])

  useEffect(() => {
    const controller = new AbortController()
    fetchCatalogSummary(controller.signal)
      .then((value) => { setSummary(value); setSummaryError(null) })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setSummaryError(reason instanceof Error ? reason.message : 'Catalog summary unavailable.')
        }
      })
    return () => controller.abort()
  }, [reload])

  useEffect(() => {
    const controller = new AbortController()
    setRequestState('loading')
    setError(null)
    fetchItems({
      search: debouncedSearch || undefined,
      quality: quality || undefined,
      inventory_type: inventoryType || undefined,
      source: source || undefined,
      min_level: minLevel === '' ? undefined : Number(minLevel),
      max_level: maxLevel === '' ? undefined : Number(maxLevel),
      verification_status: verification || undefined,
      page,
      page_size: 24,
      sort_by: 'name',
      sort_order: 'asc',
    }, controller.signal)
      .then((result) => {
        setItems(result.items)
        setTotal(result.total)
        setPages(result.pages)
        setRequestState('ready')
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return
        setError(reason instanceof Error ? reason.message : 'The catalog could not be loaded.')
        setRequestState('error')
      })
    return () => controller.abort()
  }, [debouncedSearch, quality, inventoryType, source, minLevel, maxLevel, verification, page, reload])

  useEffect(() => {
    if (selectedId === null) {
      setSelectedItem(null)
      return
    }
    const controller = new AbortController()
    setSelectedItem(null)
    setDetailLoading(true)
    setDetailError(null)
    fetchItem(selectedId, controller.signal)
      .then(setSelectedItem)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setDetailError(reason instanceof Error ? reason.message : 'Item details unavailable.')
        }
      })
      .finally(() => { if (!controller.signal.aborted) setDetailLoading(false) })
    return () => controller.abort()
  }, [selectedId])

  const qualityOptions = useMemo(
    () => summary?.items_by_quality.map((row) => row.quality) ?? [],
    [summary],
  )
  const verificationOptions = useMemo(
    () => summary?.items_by_verification_status.map((row) => row.verification_status) ?? [],
    [summary],
  )

  function resetPage() { setPage(1) }
  function closeItem() { setSelectedId(null); setSelectedItem(null) }

  return (
    <div className="app-shell">
      <header className="site-header catalog-header">
        <a className="brand" href="#planner" onClick={(event) => { event.preventDefault(); onNavigate('planner') }} aria-label="Forever BIS home">
          <span className="brand-mark" aria-hidden="true">FB</span>
          <span className="brand-copy"><strong>Forever BIS</strong><small>Forever item catalog</small></span>
        </a>
        <nav className="header-nav" aria-label="Main navigation">
          <button type="button" onClick={() => onNavigate('planner')}>Gear Planner</button>
          <a className="nav-active" href="#catalog">Item Database</a>
        </nav>
        <a className="connection-pill source-credit" href="https://thewowdb.com/" target="_blank" rel="noreferrer">
          <span className="status-dot status-good" />Data from TheWoWDB ↗
        </a>
      </header>

      <main id="catalog" className="main-content catalog-page">
        <section className="hero-panel catalog-hero">
          <div className="hero-copy">
            <p className="eyebrow">World of Warcraft: Forever · Item catalog</p>
            <h1>Explore the <span>known records.</span></h1>
            <p className="hero-description">Browse item data returned by TheWoWDB. Unreported fields and unresolved source differences stay visible as unknown or under review.</p>
          </div>
          <div className="hero-emblem" aria-hidden="true"><div className="emblem-ring"><span>FB</span></div></div>
        </section>

        <section className="catalog-summary-row" aria-label="Catalog summary">
          <div><span className="summary-number">{summary ? summary.total_items : '—'}</span><span className="summary-label">Imported items</span></div>
          <div><span className="summary-number">{summary?.items_by_verification_status.find((row) => row.verification_status === 'needs_review')?.count ?? '0'}</span><span className="summary-label">Under review</span></div>
          <div className="summary-source"><span className="summary-label">Last import</span>
            <strong>{summary?.last_import_at ? new Date(summary.last_import_at).toLocaleString() : 'No import recorded'}</strong>
          </div>
          {summaryError && <span className="summary-error" role="status">Summary unavailable: {summaryError}</span>}
        </section>

        <section className="catalog-panel" aria-labelledby="catalog-heading">
          <div className="catalog-heading-row">
            <div><p className="eyebrow">Provider records</p><h2 id="catalog-heading">Forever items</h2></div>
            <span className="muted-caption">{total} {total === 1 ? 'record' : 'records'}</span>
          </div>

          <form className="catalog-filters" onSubmit={(event) => { event.preventDefault(); resetPage(); setDebouncedSearch(search.trim()) }}>
            <label className="catalog-search-field"><span>Search item name</span>
              <input type="search" value={search} onChange={(event) => { setSearch(event.target.value); resetPage() }} placeholder="Search the catalog" />
            </label>
            <label><span>Quality</span><select value={quality} onChange={(event) => { setQuality(event.target.value); resetPage() }}>
            <option value="">All qualities</option>{qualityOptions.map((value) => <option key={value} value={value}>{qualityLabel(value)}</option>)}
            </select></label>
            <label><span>Equipment slot</span><select value={inventoryType} onChange={(event) => { setInventoryType(event.target.value); resetPage() }}>
              <option value="">All slots</option>{(summary?.inventory_types ?? []).map((value) => <option key={value} value={value}>{value}</option>)}
            </select></label>
            <label><span>Source</span><select value={source} onChange={(event) => { setSource(event.target.value); resetPage() }}>
              <option value="">All sources</option>{(summary?.active_data_sources ?? []).map((value) => <option key={value.id} value={value.name}>{value.name}</option>)}
            </select></label>
            <label><span>Min required level</span><input type="number" min="0" max="100" value={minLevel} onChange={(event) => { setMinLevel(event.target.value); resetPage() }} placeholder="Any" /></label>
            <label><span>Max required level</span><input type="number" min="0" max="100" value={maxLevel} onChange={(event) => { setMaxLevel(event.target.value); resetPage() }} placeholder="Any" /></label>
            <label><span>Verification</span><select value={verification} onChange={(event) => { setVerification(event.target.value); resetPage() }}>
              <option value="">All records</option>{verificationOptions.map((value) => <option key={value} value={value}>{verificationLabel(value)}</option>)}
            </select></label>
          </form>

          {requestState === 'loading' && <div className="catalog-state" role="status"><span className="loading-rune" aria-hidden="true">✦</span><strong>Loading catalog…</strong></div>}
          {requestState === 'error' && <div className="catalog-state catalog-error" role="alert"><strong>Catalog unavailable</strong><p>{error}</p><button type="button" className="secondary-button" onClick={() => setReload((value) => value + 1)}>Try again</button></div>}
          {requestState === 'ready' && total === 0 && <div className="catalog-state empty-catalog" role="status"><span className="empty-state-icon" aria-hidden="true">✦</span><strong>No matching item records</strong><p>Adjust the search or filters. Only records imported from the documented Forever provider API appear here.</p></div>}
          {requestState === 'ready' && total > 0 && (
            <>
              <div className="catalog-grid">{items.map((item) => <ItemCard key={item.id} item={item} onOpen={(selected) => setSelectedId(selected.id)} />)}</div>
              <div className="pagination-row"><span>Page {page} of {pages} · {total} records</span>
                <div><button type="button" className="secondary-button" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>Previous</button>
                  <button type="button" className="secondary-button" disabled={page >= pages} onClick={() => setPage((value) => value + 1)}>Next</button></div>
              </div>
            </>
          )}
        </section>

        <footer className="page-footer"><span>Forever BIS · Catalog data supplied by TheWoWDB</span><span>Not affiliated with Blizzard Entertainment</span></footer>
      </main>

      {selectedId !== null && detailLoading && <div className="detail-backdrop"><div className="catalog-state" role="status">Loading item details…</div></div>}
      {selectedId !== null && detailError && <div className="detail-backdrop" role="alert"><div className="catalog-state catalog-error"><p>{detailError}</p><button className="secondary-button" onClick={closeItem}>Close</button></div></div>}
      {selectedItem && <ItemDetail item={selectedItem} onClose={closeItem} />}
    </div>
  )
}

type PlannerPageName = 'planner' | 'catalog'
type Slot = { name: string; mark: string }

const CLASS_SPECS: Record<string, string[]> = {
  Druid: ['Balance', 'Feral', 'Restoration'],
  Hunter: ['Beast Mastery', 'Marksmanship', 'Survival'],
  Mage: ['Arcane', 'Fire', 'Frost'],
  Paladin: ['Holy', 'Protection', 'Retribution'],
  Priest: ['Discipline', 'Holy', 'Shadow'],
  Rogue: ['Assassination', 'Combat', 'Subtlety'],
  Shaman: ['Elemental', 'Enhancement', 'Restoration'],
  Warlock: ['Affliction', 'Demonology', 'Destruction'],
  Warrior: ['Arms', 'Fury', 'Protection'],
}

const LEFT_SLOTS: Slot[] = [
  { name: 'Head', mark: 'HD' }, { name: 'Neck', mark: 'NK' },
  { name: 'Shoulders', mark: 'SH' }, { name: 'Back', mark: 'BK' },
  { name: 'Chest', mark: 'CH' }, { name: 'Wrist', mark: 'WR' },
  { name: 'Hands', mark: 'HN' }, { name: 'Waist', mark: 'WA' },
  { name: 'Legs', mark: 'LG' }, { name: 'Feet', mark: 'FT' },
]

const RIGHT_SLOTS: Slot[] = [
  { name: 'Ring 1', mark: 'R1' }, { name: 'Ring 2', mark: 'R2' },
  { name: 'Trinket 1', mark: 'T1' }, { name: 'Trinket 2', mark: 'T2' },
  { name: 'Main Hand', mark: 'MH' }, { name: 'Off Hand', mark: 'OH' },
  { name: 'Ranged', mark: 'RG' },
]

function LevelProgression({ level, onChange }: { level: number; onChange: (level: number) => void }) {
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
      <p className="level-progress-note">Select any level. Gear data for this character and level is currently unavailable.</p>
    </section>
  )
}

function EquipmentSlot({ slot, onSelect }: { slot: Slot; onSelect: (slot: string) => void }) {
  return (
    <button
      className="paperdoll-slot"
      type="button"
      aria-label={`${slot.name}: recommendation unavailable. View catalog records`}
      onClick={() => onSelect(slot.name)}
    >
      <span className="paperdoll-slot-mark" aria-hidden="true">{slot.mark}</span>
      <span className="paperdoll-slot-copy"><strong>{slot.name}</strong><small>Recommendation unavailable</small></span>
      <span className="slot-unavailable" aria-hidden="true">—</span>
    </button>
  )
}

function GearPlanner({ onNavigate }: { onNavigate: (page: PlannerPageName) => void }) {
  const [characterClass, setCharacterClass] = useState('Warrior')
  const [specialization, setSpecialization] = useState(CLASS_SPECS.Warrior[0])
  const [faction, setFaction] = useState('Alliance')
  const [level, setLevel] = useState(1)
  const [activeSlot, setActiveSlot] = useState<string | null>(null)
  const [slotRecords, setSlotRecords] = useState<CatalogItem[]>([])
  const [slotState, setSlotState] = useState<RequestState>('ready')
  const [slotError, setSlotError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [selectedItem, setSelectedItem] = useState<CatalogItem | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)

  useEffect(() => {
    if (activeSlot === null) return
    const controller = new AbortController()
    setSlotState('loading')
    setSlotError(null)
    setSlotRecords([])
    fetchItems({ inventory_type: activeSlot, page: 1, page_size: 24, sort_by: 'name', sort_order: 'asc' }, controller.signal)
      .then((result) => { setSlotRecords(result.items); setSlotState('ready') })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return
        setSlotError(reason instanceof Error ? reason.message : 'Catalog records could not be loaded.')
        setSlotState('error')
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
    setSpecialization(CLASS_SPECS[nextClass][0])
  }

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
          <a href="#guides" aria-disabled="true" onClick={(event) => event.preventDefault()}>Guides</a>
          <a href="#about" aria-disabled="true" onClick={(event) => event.preventDefault()}>About</a>
        </nav>
        <span className="planner-status-pill"><span className="status-dot status-pending" />Planner preview</span>
      </header>

      <main id="planner" className="main-content planner-page">
        <section className="planner-hero">
          <div>
            <p className="eyebrow">World of Warcraft: Forever</p>
            <h1>Gear for every <span>step of the journey.</span></h1>
            <p>Set your character and level, then explore the equipment layout. Verified gear recommendations are not available yet.</p>
          </div>
          <div className="planner-crest" aria-hidden="true"><span>FB</span></div>
        </section>

        <section className="planner-config" aria-label="Character configuration">
          <label className="planner-field"><span>Class</span><select value={characterClass} onChange={(event) => changeClass(event.target.value)}>
            {Object.keys(CLASS_SPECS).map((name) => <option key={name} value={name}>{name}</option>)}
          </select></label>
          <label className="planner-field"><span>Specialization</span><select value={specialization} onChange={(event) => setSpecialization(event.target.value)}>
            {CLASS_SPECS[characterClass].map((name) => <option key={name} value={name}>{name}</option>)}
          </select></label>
          <label className="planner-field"><span>Faction</span><select value={faction} onChange={(event) => setFaction(event.target.value)}>
            <option>Alliance</option><option>Horde</option>
          </select></label>
          <div className="character-context" aria-live="polite"><span>Planning for</span><strong>{characterClass} · {specialization}</strong><small>{faction} · Level {level}</small></div>
        </section>

        <LevelProgression level={level} onChange={setLevel} />

        <section className="paperdoll-panel" aria-labelledby="equipment-heading">
          <div className="paperdoll-heading">
            <div><p className="eyebrow">Character equipment</p><h2 id="equipment-heading">Your gear at level {level}</h2></div>
            <span className="unavailable-legend"><i aria-hidden="true">—</i> Recommendation unavailable</span>
          </div>
          <div className="paperdoll-layout">
            <div className="slot-group slot-group-left" aria-label="Armor slots">
              {LEFT_SLOTS.map((slot) => <EquipmentSlot key={slot.name} slot={slot} onSelect={setActiveSlot} />)}
            </div>
            <div className="character-figure" aria-label={`Character preview: ${characterClass}`}>
              <div className="figure-halo" aria-hidden="true" />
              <div className="figure-silhouette" aria-hidden="true"><span className="figure-head" /><span className="figure-body" /><span className="figure-cape" /></div>
              <span className="figure-class">{characterClass}</span>
              <span className="figure-level">Level {level}</span>
            </div>
            <div className="slot-group slot-group-right" aria-label="Jewelry and weapon slots">
              {RIGHT_SLOTS.map((slot) => <EquipmentSlot key={slot.name} slot={slot} onSelect={setActiveSlot} />)}
            </div>
          </div>
          <div className="recommendation-unavailable" role="status">
            <span className="empty-state-icon" aria-hidden="true">✦</span>
            <div><strong>No verified gear recommendations for this selection</strong><p>The catalog currently contains only three records, all marked for review. No item is being presented as best-in-slot, an alternative, an easy pickup, or an upgrade.</p></div>
          </div>
        </section>

        <footer className="page-footer"><span>Forever BIS · Level progression planner</span><span>Catalog records are not gear recommendations</span></footer>
      </main>

      {activeSlot !== null && (
        <div className="detail-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setActiveSlot(null)}>
          <section className="slot-record-panel" role="dialog" aria-modal="true" aria-labelledby="slot-record-heading">
            <button className="detail-close" type="button" aria-label="Close slot records" onClick={() => setActiveSlot(null)}>×</button>
            <p className="eyebrow">{characterClass} · {specialization} · {faction} · Level {level}</p>
            <h2 id="slot-record-heading">{activeSlot}</h2>
            <div className="slot-not-recommendation"><strong>Recommendation unavailable</strong><span>These are provider catalog records for this slot, not recommendations for your character.</span></div>
            {slotState === 'loading' && <div className="catalog-state" role="status">Loading matching catalog records…</div>}
            {slotState === 'error' && <div className="catalog-state catalog-error" role="alert">{slotError}</div>}
            {slotState === 'ready' && slotRecords.length === 0 && <div className="catalog-state" role="status"><strong>No matching catalog records reported</strong><p>This does not establish that the slot has no obtainable items.</p></div>}
            {slotState === 'ready' && slotRecords.length > 0 && (
              <div className="slot-record-list">
                {slotRecords.map((item) => <button className="slot-record-card" type="button" key={item.id} onClick={() => { setActiveSlot(null); setSelectedId(item.id) }}>
                  {item.icon_url ? <img src={item.icon_url} alt="" /> : <span className="slot-record-no-icon" aria-hidden="true">?</span>}
                  <span><strong>{item.name}</strong><small>{item.quality ?? 'Quality unknown'} · {item.item_level === null ? 'Item level unknown' : `Item level ${item.item_level}`}</small><small>{item.verification_status === 'needs_review' ? 'Needs review' : 'Provider reported'}</small></span>
                </button>)}
              </div>
            )}
            <button className="secondary-button" type="button" onClick={() => { setActiveSlot(null); onNavigate('catalog') }}>Open Item Database</button>
          </section>
        </div>
      )}
      {selectedId !== null && detailLoading && <div className="detail-backdrop"><div className="catalog-state" role="status">Loading item details…</div></div>}
      {selectedId !== null && detailError && <div className="detail-backdrop" role="alert"><div className="catalog-state catalog-error"><p>{detailError}</p><button className="secondary-button" onClick={() => setSelectedId(null)}>Close</button></div></div>}
      {selectedItem && <ItemDetail item={selectedItem} onClose={() => { setSelectedId(null); setSelectedItem(null) }} />}
    </div>
  )
}

export default function App() {
  const [activePage, setActivePage] = useState<PlannerPageName>('planner')
  return activePage === 'planner'
    ? <GearPlanner onNavigate={setActivePage} />
    : <CatalogPage onNavigate={setActivePage} />
}
