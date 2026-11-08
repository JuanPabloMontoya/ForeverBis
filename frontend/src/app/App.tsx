import { useEffect, useMemo, useState } from 'react'
import {
  fetchCatalogSummary,
  fetchItem,
  fetchItems,
  type CatalogItem,
  type CatalogSummary,
} from '../api/catalog'
import GearPlanner from '../features/planner/GearPlanner'

type RequestState = 'loading' | 'ready' | 'error'
type PlannerPageName = 'planner' | 'catalog'

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
  if (status === 'verified') return 'Verified'
  if (status === 'needs_review') return 'Needs review'
  if (status === 'provider_reported') return 'Provider reported'
  return 'Verification unknown'
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
          {item.armor_value !== null && <div><dt>Armor</dt><dd>{item.armor_value}</dd></div>}
          <div><dt>Weapon type</dt><dd>{item.weapon_type ?? 'Unknown'}</dd></div>
          {item.weapon_damage_min !== null && item.weapon_damage_max !== null && <div><dt>Weapon damage</dt><dd>{item.weapon_damage_min}–{item.weapon_damage_max}</dd></div>}
          {item.weapon_speed !== null && <div><dt>Weapon speed</dt><dd>{item.weapon_speed}</dd></div>}
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
        <section className="detail-subsection">
          <h3>Acquisition</h3>
          {item.acquisitions.length ? (
            <ul>{item.acquisitions.map((entry, index) => <li key={`${entry.acquisition_source.source_type}-${index}`}>
              {entry.acquisition_source.source_type}: {entry.acquisition_source.name ?? 'Name unknown'} · {entry.verification_status}
            </li>)}</ul>
          ) : <p>Acquisition source is not verified in the catalog.</p>}
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
          {item.wowhead_url && item.verification_status === 'verified' && (
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

export default function App() {
  const [activePage, setActivePage] = useState<PlannerPageName>('planner')
  return activePage === 'planner'
    ? <GearPlanner onNavigate={setActivePage} />
    : <CatalogPage onNavigate={setActivePage} />
}
