import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CatalogItem, CatalogPage, CatalogSummary } from '../api/catalog'
import * as catalogApi from '../api/catalog'
import App from './App'

vi.mock('../api/catalog', () => ({
  fetchCatalogSummary: vi.fn(),
  fetchItems: vi.fn(),
  fetchItem: vi.fn(),
}))

const api = vi.mocked(catalogApi)

const summary: CatalogSummary = {
  total_items: 2,
  items_by_quality: [{ quality: 'common', count: 2 }],
  items_by_verification_status: [{ verification_status: 'needs_review', count: 1 }],
  inventory_types: ['Main Hand', 'Two-Hand'],
  last_import_at: '2026-11-08T02:35:07Z',
  active_data_sources: [{
    id: 1,
    name: 'TheWoWDB',
    base_url: 'https://thewowdb.com/',
    terms_url: 'https://thewowdb.com/developers/#terms',
    attribution_text: 'Data from TheWoWDB (thewowdb.com)',
    license_status: 'permitted_with_attribution',
    last_checked_at: '2026-11-08T02:35:07Z',
  }],
}

const item: CatalogItem = {
  id: 1,
  source_item_id: 25,
  name: 'Worn Shortsword',
  quality: 'common',
  item_level: 2,
  required_level: null,
  inventory_type: 'Main Hand',
  armor_type: null,
  weapon_type: 'One-Handed Sword',
  icon_url: 'https://render.worldofwarcraft.com/us/icons/56/inv_sword_04.jpg',
  source_item_url: 'https://thewowdb.com/wow-forever/item/worn-shortsword-25/',
  wowhead_url: 'https://www.wowhead.com/forever/item=25/worn-shortsword',
  availability_status: 'unknown',
  verification_status: 'needs_review',
  created_at: '2026-11-08T02:35:07Z',
  updated_at: '2026-11-08T02:35:07Z',
  source: summary.active_data_sources[0],
  game_version: { game_key: 'wow_forever', build: 'wow_classic_beta-1.60.1.70532', observed_at: '2026-11-08T02:35:07Z' },
  stats: [],
  effects: [],
  restrictions: [],
  quality_issues: [
    {
      field_name: 'required_level',
      issue_code: 'list_detail_conflict',
      message: 'List and detail disagree; required level stays unknown pending review.',
      observed_values: { list: 1, detail: null },
    },
    {
      field_name: 'stats',
      issue_code: 'empty_array_semantics_unverified',
      message: 'No stat entries were reported; this does not prove the item has no stats.',
      observed_values: [],
    },
    {
      field_name: 'classes',
      issue_code: 'empty_array_semantics_unverified',
      message: 'No class restrictions were reported; unrestricted use is not established.',
      observed_values: [],
    },
    {
      field_name: 'effects',
      issue_code: 'empty_array_semantics_unverified',
      message: 'No effect entries were reported; this does not prove the item has no effects.',
      observed_values: [],
    },
  ],
}

const pageOne: CatalogPage = { items: [item], page: 1, page_size: 24, total: 2, pages: 2 }
const pageTwo: CatalogPage = { items: [{ ...item, id: 2, source_item_id: 35, name: 'Bent Staff' }], page: 2, page_size: 24, total: 2, pages: 2 }

async function renderCatalog() {
  render(<App />)
  fireEvent.click(screen.getByRole('button', { name: 'Item Database' }))
  await screen.findByRole('heading', { name: 'Forever items' })
}

beforeEach(() => {
  vi.clearAllMocks()
  api.fetchCatalogSummary.mockResolvedValue(summary)
  api.fetchItems.mockResolvedValue(pageOne)
  api.fetchItem.mockResolvedValue(item)
})

afterEach(() => vi.restoreAllMocks())

describe('Forever item catalog', () => {
  it('renders provider items, counts and visible attribution', async () => {
    await renderCatalog()
    expect(await screen.findByRole('button', { name: 'View Worn Shortsword details' })).toBeInTheDocument()
    expect(screen.getByText('2 records')).toBeInTheDocument()
    expect(screen.getAllByText('Data from TheWoWDB').length).toBeGreaterThan(0)
    expect(screen.getByText('Needs review', { selector: '.verification-badge' })).toBeInTheDocument()
  })

  it('searches the catalog by name through the API filter', async () => {
    await renderCatalog()
    await screen.findByRole('button', { name: 'View Worn Shortsword details' })
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search item name' }), {
      target: { value: 'shortsword' },
    })
    await waitFor(() => expect(api.fetchItems).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: 'shortsword', page: 1 }),
      expect.any(AbortSignal),
    ))
  })

  it('sends quality, slot, level, source and verification filters', async () => {
    await renderCatalog()
    await screen.findByRole('button', { name: 'View Worn Shortsword details' })
    fireEvent.change(screen.getByRole('combobox', { name: 'Quality' }), { target: { value: 'common' } })
    fireEvent.change(screen.getByRole('combobox', { name: 'Equipment slot' }), { target: { value: 'Main Hand' } })
    fireEvent.change(screen.getByRole('combobox', { name: 'Source' }), { target: { value: 'TheWoWDB' } })
    fireEvent.change(screen.getByRole('combobox', { name: 'Verification' }), { target: { value: 'needs_review' } })
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Min required level' }), { target: { value: '1' } })
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Max required level' }), { target: { value: '10' } })
    await waitFor(() => expect(api.fetchItems).toHaveBeenLastCalledWith(
      expect.objectContaining({
        quality: 'common',
        inventory_type: 'Main Hand',
        source: 'TheWoWDB',
        verification_status: 'needs_review',
        min_level: 1,
        max_level: 10,
      }),
      expect.any(AbortSignal),
    ))
  })

  it('paginates to the next server page', async () => {
    api.fetchItems.mockImplementation(async (filters) => filters.page === 2 ? pageTwo : pageOne)
    await renderCatalog()
    await screen.findByRole('button', { name: 'View Worn Shortsword details' })
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(await screen.findByRole('button', { name: 'View Bent Staff details' })).toBeInTheDocument()
    expect(api.fetchItems).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 }), expect.any(AbortSignal))
  })

  it('loads item details and only renders a mapped Forever Wowhead link', async () => {
    await renderCatalog()
    fireEvent.click(await screen.findByRole('button', { name: 'View Worn Shortsword details' }))
    const dialog = await screen.findByRole('dialog', { name: 'Worn Shortsword' })
    expect(within(dialog).getByText('Required level under review · list 1 / detail unknown')).toBeInTheDocument()
    expect(within(dialog).getByText(/No stats reported; completeness is unverified/)).toBeInTheDocument()
    expect(within(dialog).getAllByText(/unrestricted use is not established/)).toHaveLength(2)
    expect(within(dialog).getByRole('link', { name: /Wowhead Forever/ })).toHaveAttribute('href', item.wowhead_url)
    expect(api.fetchItem).toHaveBeenCalledWith(item.id, expect.any(AbortSignal))
  })

  it('shows unknown fields without treating them as absent restrictions or stats', async () => {
    api.fetchItems.mockResolvedValue({ ...pageOne, items: [{
      ...item,
      id: 9,
      source_item_id: 900,
      name: 'Unspecified item',
      quality: null,
      item_level: null,
      inventory_type: null,
      icon_url: null,
      wowhead_url: null,
      stats: [],
      restrictions: [],
      quality_issues: [],
    }] })
    await renderCatalog()
    expect(await screen.findByText('Quality unknown')).toBeInTheDocument()
    expect(screen.getByText(/Item level unknown/)).toBeInTheDocument()
    expect(screen.getByText(/Slot unknown/)).toBeInTheDocument()
  })

  it('shows loading, empty and error states', async () => {
    let resolveList!: (value: CatalogPage) => void
    api.fetchItems.mockReturnValue(new Promise((resolve) => { resolveList = resolve }))
    await renderCatalog()
    expect(screen.getByRole('status')).toHaveTextContent('Loading catalog')
    resolveList({ ...pageOne, items: [], total: 0, pages: 0 })
    expect(await screen.findByText('No matching item records')).toBeInTheDocument()

    api.fetchItems.mockRejectedValue(new Error('API offline'))
    fireEvent.click(screen.getByRole('searchbox', { name: 'Search item name' }))
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search item name' }), { target: { value: 'broken' } })
    expect(await screen.findByRole('alert')).toHaveTextContent('API offline')
  })
})

describe('Gear Planner', () => {
  it('is the homepage and offers all nine classes and both factions', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /Gear for every step of the journey/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Item Database' })).toBeInTheDocument()
    expect(screen.getAllByRole('option', { name: /^(Druid|Hunter|Mage|Paladin|Priest|Rogue|Shaman|Warlock|Warrior)$/ })).toHaveLength(9)
    expect(screen.getByRole('combobox', { name: 'Faction' })).toHaveDisplayValue('Alliance')
  })

  it('provides 60 selectable levels with highlighted selection and keyboard boundaries', () => {
    render(<App />)
    const progression = screen.getByRole('group', { name: 'Choose a character level' })
    const buttons = within(progression).getAllByRole('button', { name: /^Level \d+$/ })
    expect(buttons).toHaveLength(60)
    expect(within(progression).getByRole('button', { name: 'Level 1' })).toHaveAttribute('aria-pressed', 'true')

    fireEvent.click(within(progression).getByRole('button', { name: 'Level 42' }))
    expect(within(progression).getByRole('button', { name: 'Level 42' })).toHaveAttribute('aria-pressed', 'true')
    fireEvent.keyDown(within(progression).getByRole('button', { name: 'Level 42' }), { key: 'ArrowRight' })
    expect(within(progression).getByRole('button', { name: 'Level 43' })).toHaveAttribute('aria-pressed', 'true')
    fireEvent.keyDown(within(progression).getByRole('button', { name: 'Level 43' }), { key: 'End' })
    expect(within(progression).getByRole('button', { name: 'Level 60' })).toHaveAttribute('aria-pressed', 'true')
    fireEvent.keyDown(within(progression).getByRole('button', { name: 'Level 60' }), { key: 'ArrowRight' })
    expect(within(progression).getByRole('button', { name: 'Level 60' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('updates specialization options when class changes and keeps character context visible', () => {
    render(<App />)
    fireEvent.change(screen.getByRole('combobox', { name: 'Class' }), { target: { value: 'Druid' } })
    expect(screen.getByRole('combobox', { name: 'Specialization' })).toHaveDisplayValue('Balance')
    expect(screen.getAllByRole('option', { name: /^(Balance|Feral|Restoration)$/ })).toHaveLength(3)
    fireEvent.change(screen.getByRole('combobox', { name: 'Specialization' }), { target: { value: 'Restoration' } })
    fireEvent.change(screen.getByRole('combobox', { name: 'Faction' }), { target: { value: 'Horde' } })
    expect(screen.getByText('Druid · Restoration')).toBeInTheDocument()
    expect(screen.getByText('Horde · Level 1')).toBeInTheDocument()
  })

  it('shows all 17 slots as unavailable and opens real catalog item details from a matching slot', async () => {
    render(<App />)
    expect(document.querySelectorAll('.paperdoll-slot')).toHaveLength(17)
    const mainHand = screen.getByRole('button', { name: /Main Hand: recommendation unavailable/ })
    fireEvent.click(mainHand)
    expect(await screen.findByRole('heading', { name: 'Main Hand' })).toBeInTheDocument()
    expect(screen.getByText(/not recommendations for your character/)).toBeInTheDocument()
    fireEvent.click(await screen.findByRole('button', { name: /Worn Shortsword/ }))
    expect(await screen.findByRole('dialog', { name: 'Worn Shortsword' })).toBeInTheDocument()
    expect(api.fetchItems).toHaveBeenCalledWith(expect.objectContaining({ inventory_type: 'Main Hand' }), expect.any(AbortSignal))
    expect(api.fetchItem).toHaveBeenCalledWith(item.id, expect.any(AbortSignal))
  })

  it('distinguishes no matching catalog records from a recommendation or empty equipped slot', async () => {
    api.fetchItems.mockResolvedValue({ ...pageOne, items: [], total: 0, pages: 0 })
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: /Head: recommendation unavailable/ }))
    expect(await screen.findByText('No matching catalog records reported')).toBeInTheDocument()
    expect(screen.getByText('This does not establish that the slot has no obtainable items.')).toBeInTheDocument()
  })

  it('keeps the item database secondary and provides navigation back to the planner', async () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Item Database' }))
    expect(await screen.findByRole('heading', { name: 'Forever items' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Gear Planner' }))
    expect(await screen.findByRole('heading', { name: /Gear for every step of the journey/ })).toBeInTheDocument()
  })
})
