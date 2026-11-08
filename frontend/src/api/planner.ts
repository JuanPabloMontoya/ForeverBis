import type { CatalogItem } from './catalog'

export type ScoringProfile = {
  id: number
  class_name: string
  specialization: string
  role: string | null
  version: string
  active: boolean
  provisional: boolean
  assumptions: string
  stat_weights: Record<string, number>
  adjustments: Record<string, number>
}

export type PlannerCharacter = {
  class_name: string
  specialization: string
  faction: 'Alliance' | 'Horde'
  level: number
}

export type ScoreExplanation = {
  item_id: number
  item_name: string
  status: 'scored' | 'provisional' | 'incomplete' | 'ineligible'
  score: number | null
  eligibility: { status: 'eligible' | 'ineligible' | 'unknown'; reasons: string[] }
  contributions: Array<{
    stat_type: string
    value: number
    weight: number
    contribution: number
  }>
  missing_information: string[]
  unsupported_statistics: string[]
  unweighted_statistics: string[]
  provisional: boolean
  profile_version: string
  calculation_version: string
}

export type PlannerCandidate = {
  item: CatalogItem
  result: ScoreExplanation
  score_difference: number | null
}

export type PlannerSlot = {
  slot: string
  slot_family: string
  status: 'recommended' | 'insufficient_data' | 'unavailable'
  recommendation: PlannerCandidate | null
  alternatives: PlannerCandidate[]
  eligible_count: number
  incomplete_count: number
  explanation: string[]
}

export type GearPlan = {
  character: PlannerCharacter
  profile_version: string
  profile_provisional: boolean
  profile_configured: boolean
  profile_assumptions: string
  slots: PlannerSlot[]
}

export type SuggestionRequest = {
  class_name: string
  specialization: string
  faction: 'Alliance' | 'Horde'
  character_level: number
  equipment_slot: string
  suggested_item_name: string
  wowhead_url: string
  explanation?: string
  supporting_evidence?: string
}

export type SuggestionReceipt = {
  id: string
  status: string
  duplicate_flagged: boolean
  submitted_at: string
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { Accept: 'application/json' },
    signal,
  })
  if (!response.ok) throw new Error(`Planner request failed (${response.status})`)
  return (await response.json()) as T
}

export function fetchScoringProfiles(signal?: AbortSignal): Promise<ScoringProfile[]> {
  return getJson<ScoringProfile[]>('/api/v1/scoring-profiles', signal)
}

export function fetchGearPlan(
  character: PlannerCharacter,
  signal?: AbortSignal,
): Promise<GearPlan> {
  const query = new URLSearchParams({
    class_name: character.class_name,
    specialization: character.specialization,
    faction: character.faction,
    level: String(character.level),
  })
  return getJson<GearPlan>(`/api/v1/planner/recommendations?${query.toString()}`, signal)
}

export async function submitItemSuggestion(
  suggestion: SuggestionRequest,
): Promise<SuggestionReceipt> {
  const response = await fetch(`${apiBaseUrl}/api/v1/suggestions`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(suggestion),
  })
  if (!response.ok) throw new Error(`Suggestion could not be submitted (${response.status})`)
  return (await response.json()) as SuggestionReceipt
}
