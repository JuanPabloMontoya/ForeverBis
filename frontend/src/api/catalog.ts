export type CatalogSource = {
  id: number
  name: string
  base_url: string
  terms_url: string
  attribution_text: string
  license_status: string
}

export type CatalogItem = {
  id: number
  source_item_id: number
  name: string
  quality: string | null
  item_level: number | null
  required_level: number | null
  inventory_type: string | null
  armor_type: string | null
  weapon_type: string | null
  icon_url: string | null
  source_item_url: string | null
  wowhead_url: string | null
  armor_value: number | null
  weapon_damage_min: number | null
  weapon_damage_max: number | null
  weapon_speed: number | null
  availability_status: string
  verification_status: string
  eligibility_status: string
  statistics_status: string
  last_validated_at: string | null
  created_at: string
  updated_at: string
  source: CatalogSource
  game_version: { game_key: string; build: string | null; observed_at: string }
  stats: Array<{ stat_type: string; value: number }>
  effects: Array<{ effect_type: string; description: string | null; spell_id: number | null }>
  restrictions: Array<{
    restriction_type: string
    restriction_value: string
    verification_status: string
  }>
  acquisitions: Array<{
    verification_status: string
    requirements: string | null
    acquisition_source: {
      source_type: string
      name: string | null
      external_id: string | null
      location: string | null
      source_url: string | null
      verification_status: string
    }
  }>
  quality_issues: Array<{
    field_name: string
    issue_code: string
    message: string
    observed_values: Record<string, unknown> | unknown[] | null
  }>
}

export type CatalogPage = {
  items: CatalogItem[]
  page: number
  page_size: number
  total: number
  pages: number
}

export type CatalogSummary = {
  total_items: number
  items_by_quality: Array<{ quality: string; count: number }>
  items_by_verification_status: Array<{ verification_status: string; count: number }>
  inventory_types: string[]
  last_import_at: string | null
  active_data_sources: Array<CatalogSource & { last_checked_at: string | null }>
}

export type ItemFilters = {
  search?: string
  quality?: string
  inventory_type?: string
  min_level?: number
  max_level?: number
  source?: string
  verification_status?: string
  page?: number
  page_size?: number
  sort_by?: 'name' | 'quality' | 'item_level' | 'required_level' | 'updated_at'
  sort_order?: 'asc' | 'desc'
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { Accept: 'application/json' },
    signal,
  })
  if (!response.ok) throw new Error(`Catalog request failed (${response.status})`)
  return (await response.json()) as T
}

export function fetchItems(filters: ItemFilters, signal?: AbortSignal): Promise<CatalogPage> {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== '') query.set(key, String(value))
  }
  return getJson<CatalogPage>(`/api/v1/items?${query.toString()}`, signal)
}

export function fetchItem(itemId: number, signal?: AbortSignal): Promise<CatalogItem> {
  return getJson<CatalogItem>(`/api/v1/items/${itemId}`, signal)
}

export function fetchCatalogSummary(signal?: AbortSignal): Promise<CatalogSummary> {
  return getJson<CatalogSummary>('/api/v1/catalog/summary', signal)
}
