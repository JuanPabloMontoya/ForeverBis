import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CatalogItem, CatalogPage, CatalogSummary } from '../api/catalog'
import * as catalogApi from '../api/catalog'
import type { GearPlan, PlannerCandidate, PlannerSlot, ScoringProfile } from '../api/planner'
import * as plannerApi from '../api/planner'
import App from './App'

vi.mock('../api/catalog', () => ({
  fetchCatalogSummary: vi.fn(),
  fetchItems: vi.fn(),
  fetchItem: vi.fn(),
}))
vi.mock('../api/planner', () => ({
  fetchScoringProfiles: vi.fn(),
  fetchGearPlan: vi.fn(),
  submitItemSuggestion: vi.fn(),
}))

const api = vi.mocked(catalogApi)
const planner = vi.mocked(plannerApi)

const profiles: ScoringProfile[] = [
  ['Druid', ['Balance', 'Feral', 'Restoration']],
  ['Hunter', ['Beast Mastery', 'Marksmanship', 'Survival']],
  ['Mage', ['Arcane', 'Fire', 'Frost']],
  ['Paladin', ['Holy', 'Protection', 'Retribution']],
  ['Priest', ['Discipline', 'Holy', 'Shadow']],
  ['Rogue', ['Assassination', 'Combat', 'Subtlety']],
  ['Shaman', ['Elemental', 'Enhancement', 'Restoration']],
  ['Warlock', ['Affliction', 'Demonology', 'Destruction']],
  ['Warrior', ['Arms', 'Fury', 'Protection']],
].flatMap(([className, specs]) => (specs as string[]).map((specialization, index) => ({
  id: index + 1,
  class_name: className as string,
  specialization,
  role: null,
  version: 'v1-provisional',
  active: true,
  provisional: true,
  assumptions: 'No validated weights.',
  stat_weights: {},
  adjustments: {},
})))

const slotNames = ['Head', 'Neck', 'Shoulders', 'Back', 'Chest', 'Wrist', 'Hands', 'Waist', 'Legs', 'Feet', 'Ring 1', 'Ring 2', 'Trinket 1', 'Trinket 2', 'Main Hand', 'Off Hand', 'Ranged']
const emptyPlan: GearPlan = {
  character: { class_name: 'Warrior', specialization: 'Arms', faction: 'Alliance', level: 1 },
  profile_version: 'v1-provisional',
  profile_provisional: true,
  profile_configured: false,
  profile_assumptions: 'No validated weights.',
  slots: slotNames.map((slot): PlannerSlot => ({
    slot, slot_family: slot, status: 'unavailable', recommendation: null, alternatives: [],
    eligible_count: 0, incomplete_count: 0, explanation: ['No verified candidate data is available.'],
  })),
}

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
  armor_value: null,
  weapon_damage_min: null,
  weapon_damage_max: null,
  weapon_speed: null,
  availability_status: 'unknown',
  verification_status: 'needs_review',
  eligibility_status: 'unknown',
  statistics_status: 'unknown',
  last_validated_at: null,
  created_at: '2026-11-08T02:35:07Z',
  updated_at: '2026-11-08T02:35:07Z',
  source: summary.active_data_sources[0],
  game_version: { game_key: 'wow_forever', build: 'wow_classic_beta-1.60.1.70532', observed_at: '2026-11-08T02:35:07Z' },
  stats: [],
  effects: [],
  restrictions: [],
  acquisitions: [],
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
const verifiedFixtureItem: CatalogItem = {
  ...item,
  name: 'Synthetic verified helm fixture',
  inventory_type: 'Head',
  required_level: 1,
  availability_status: 'available',
  verification_status: 'verified',
  eligibility_status: 'verified',
  statistics_status: 'verified',
  wowhead_url: null,
  quality_issues: [],
  stats: [{ stat_type: 'Intellect', value: 3 }],
}
const validCandidate: PlannerCandidate = {
  item: verifiedFixtureItem,
  result: {
    item_id: verifiedFixtureItem.id,
    item_name: verifiedFixtureItem.name,
    status: 'scored',
    score: 6,
    eligibility: { status: 'eligible', reasons: ['Verified test fixture.'] },
    contributions: [{ stat_type: 'intellect', value: 3, weight: 2, contribution: 6 }],
    missing_information: [],
    unsupported_statistics: [],
    unweighted_statistics: [],
    provisional: false,
    profile_version: 'fixture-profile-v1',
    calculation_version: 'weighted-item-score-v1',
  },
  score_difference: null,
}
const planWithRecommendation: GearPlan = {
  ...emptyPlan,
  profile_provisional: false,
  profile_configured: true,
  profile_version: 'fixture-profile-v1',
  slots: emptyPlan.slots.map((slot) => slot.slot === 'Head'
    ? { ...slot, status: 'recommended', recommendation: validCandidate, explanation: ['Backend scored verified fixture.'] }
    : slot),
}

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
  planner.fetchScoringProfiles.mockResolvedValue(profiles)
  planner.fetchGearPlan.mockResolvedValue(emptyPlan)
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

  it('loads item details and hides external links on unverified catalog rows', async () => {
    await renderCatalog()
    fireEvent.click(await screen.findByRole('button', { name: 'View Worn Shortsword details' }))
    const dialog = await screen.findByRole('dialog', { name: 'Worn Shortsword' })
    expect(within(dialog).getByText('Required level under review · list 1 / detail unknown')).toBeInTheDocument()
    expect(within(dialog).getByText(/No stats reported; completeness is unverified/)).toBeInTheDocument()
    expect(within(dialog).getAllByText(/unrestricted use is not established/)).toHaveLength(2)
    expect(within(dialog).queryByRole('link', { name: /Wowhead Forever/ })).not.toBeInTheDocument()
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
  it('is the homepage and populates all nine classes from scoring profiles', async () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /Gear for every step of the journey/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Item Database' })).toBeInTheDocument()
    const classSelector = await screen.findByRole('combobox', { name: 'Class' })
    expect(within(classSelector).getAllByRole('option')).toHaveLength(9)
    expect(screen.getByRole('combobox', { name: 'Faction' })).toHaveDisplayValue('Alliance')
    await waitFor(() => expect(planner.fetchGearPlan).toHaveBeenCalledWith(
      { class_name: 'Warrior', specialization: 'Arms', faction: 'Alliance', level: 1 },
      expect.any(AbortSignal),
    ))
  })

  it('provides 60 selectable levels, keyboard boundaries and a previous/next control', async () => {
    render(<App />)
    const progression = screen.getByRole('group', { name: 'Choose a character level' })
    const buttons = within(progression).getAllByRole('button', { name: /^Level \d+$/ })
    expect(buttons).toHaveLength(60)
    expect(within(progression).getByRole('button', { name: 'Level 1' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Previous level' })).toBeDisabled()
    fireEvent.click(within(progression).getByRole('button', { name: 'Level 42' }))
    expect(within(progression).getByRole('button', { name: 'Level 42' })).toHaveAttribute('aria-pressed', 'true')
    fireEvent.keyDown(within(progression).getByRole('button', { name: 'Level 42' }), { key: 'ArrowRight' })
    expect(within(progression).getByRole('button', { name: 'Level 43' })).toHaveAttribute('aria-pressed', 'true')
    fireEvent.keyDown(within(progression).getByRole('button', { name: 'Level 43' }), { key: 'End' })
    expect(within(progression).getByRole('button', { name: 'Level 60' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Next level' })).toBeDisabled()
    fireEvent.keyDown(within(progression).getByRole('button', { name: 'Level 60' }), { key: 'ArrowRight' })
    expect(within(progression).getByRole('button', { name: 'Level 60' })).toHaveAttribute('aria-pressed', 'true')
    await waitFor(() => expect(planner.fetchGearPlan).toHaveBeenLastCalledWith(
      { class_name: 'Warrior', specialization: 'Arms', faction: 'Alliance', level: 60 },
      expect.any(AbortSignal),
    ))
  })

  it('updates class-specific specs and refreshes on class, faction and level changes', async () => {
    render(<App />)
    const classSelector = await screen.findByRole('combobox', { name: 'Class' })
    fireEvent.change(classSelector, { target: { value: 'Druid' } })
    expect(screen.getByRole('combobox', { name: 'Specialization' })).toHaveDisplayValue('Balance')
    expect(within(screen.getByRole('combobox', { name: 'Specialization' })).getAllByRole('option')).toHaveLength(3)
    fireEvent.change(screen.getByRole('combobox', { name: 'Specialization' }), { target: { value: 'Restoration' } })
    fireEvent.change(screen.getByRole('combobox', { name: 'Faction' }), { target: { value: 'Horde' } })
    fireEvent.click(screen.getByRole('button', { name: 'Level 24' }))
    await waitFor(() => expect(planner.fetchGearPlan).toHaveBeenLastCalledWith(
      { class_name: 'Druid', specialization: 'Restoration', faction: 'Horde', level: 24 },
      expect.any(AbortSignal),
    ))
    expect(screen.getByText(/Druid.*Restoration/)).toBeInTheDocument()
    expect(screen.getByText(/Horde.*Level 24/)).toBeInTheDocument()
  })

  it('renders all 17 slots and clear no-recommendation states', async () => {
    render(<App />)
    await screen.findByRole('combobox', { name: 'Class' })
    expect(document.querySelectorAll('.paperdoll-slot')).toHaveLength(17)
    expect(await screen.findByText(/no scoring weights configured/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Main Hand: No recommendation available/ })).toBeInTheDocument()
  })

  it('shows a valid backend recommendation, alternative and item score details', async () => {
    const alternative: PlannerCandidate = {
      ...validCandidate,
      item: { ...verifiedFixtureItem, id: 2, name: 'Synthetic alternative fixture' },
      result: { ...validCandidate.result, item_id: 2, item_name: 'Synthetic alternative fixture', score: 4 },
      score_difference: 2,
    }
    planner.fetchGearPlan.mockResolvedValue({
      ...planWithRecommendation,
      slots: planWithRecommendation.slots.map((slot) => slot.slot === 'Head'
        ? { ...slot, alternatives: [alternative] }
        : slot),
    })
    render(<App />)
    const recommendedSlot = await screen.findByRole('button', { name: /Head: Synthetic verified helm fixture/ })
    expect(recommendedSlot).toHaveTextContent('6')
    fireEvent.click(recommendedSlot)
    expect(await screen.findByText('Recommended item')).toBeInTheDocument()
    expect(screen.getByText('Alternatives')).toBeInTheDocument()
    expect(screen.getByText('Synthetic alternative fixture')).toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('button', { name: 'View item and score details' })[0])
    expect(await screen.findByRole('heading', { name: 'Worn Shortsword' })).toBeInTheDocument()
    expect(document.querySelector('.planner-score-detail')).toHaveTextContent(/Score 6.*Eligibility: eligible/)
    expect(screen.getByText('intellect: 3 × 2 = 6')).toBeInTheDocument()
    expect(screen.getByText('Acquisition source is not verified in the catalog.')).toBeInTheDocument()
  })

  it('explains unknown eligibility and keeps incomplete candidates out of recommendations', async () => {
    planner.fetchGearPlan.mockResolvedValue({
      ...emptyPlan,
      slots: emptyPlan.slots.map((slot) => slot.slot === 'Head'
        ? { ...slot, status: 'insufficient_data', incomplete_count: 1, explanation: ['Equipment eligibility is unknown.', 'Statistics completeness is not verified.'] }
        : slot),
    })
    render(<App />)
    const head = await screen.findByRole('button', { name: /Head: Insufficient verified data/ })
    expect(head).toBeInTheDocument()
    fireEvent.click(head)
    expect(await screen.findAllByText(/Equipment eligibility is unknown/)).toHaveLength(2)
    expect(screen.queryByText('Recommended item')).not.toBeInTheDocument()
  })

  it('shows recommendation API errors without fabricating slot contents', async () => {
    planner.fetchGearPlan.mockRejectedValue(new Error('API offline'))
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent('API offline')
    expect(screen.getByRole('button', { name: /Main Hand: No recommendation available/ })).toBeInTheDocument()
  })

  it('submits a Wowhead Forever contribution for the selected planner context', async () => {
    planner.submitItemSuggestion.mockResolvedValue({
      id: '00000000-0000-0000-0000-000000000001',
      status: 'pending_review',
      duplicate_flagged: false,
      submitted_at: '2026-11-08T00:00:00Z',
    })
    render(<App />)
    const head = await screen.findByRole('button', { name: /Head: No recommendation available/ })
    fireEvent.click(head)
    fireEvent.change(screen.getByLabelText('Item name'), { target: { value: 'Suggested test item' } })
    fireEvent.change(screen.getByLabelText('Wowhead Forever item URL'), {
      target: { value: 'https://www.wowhead.com/forever/item=123/test-item' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Submit for review' }))
    expect(await screen.findByText(/was submitted for review/)).toBeInTheDocument()
    expect(planner.submitItemSuggestion).toHaveBeenCalledWith(expect.objectContaining({
      class_name: 'Warrior', specialization: 'Arms', faction: 'Alliance',
      character_level: 1, equipment_slot: 'head', suggested_item_name: 'Suggested test item',
    }))
  })

  it('reports profile API errors and keeps selectors unavailable', async () => {
    planner.fetchScoringProfiles.mockRejectedValue(new Error('profiles offline'))
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent('profiles offline')
    expect(screen.getByRole('combobox', { name: 'Class' })).toBeDisabled()
    expect(planner.fetchGearPlan).not.toHaveBeenCalled()
  })

  it('keeps the item database secondary and navigation working', async () => {
    render(<App />)
    await screen.findByRole('combobox', { name: 'Class' })
    fireEvent.click(screen.getByRole('button', { name: 'Item Database' }))
    expect(await screen.findByRole('heading', { name: 'Forever items' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Gear Planner' }))
    expect(await screen.findByRole('heading', { name: /Gear for every step of the journey/ })).toBeInTheDocument()
  })
})
