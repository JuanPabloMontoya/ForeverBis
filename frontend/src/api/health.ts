export type HealthResponse = {
  status: 'healthy' | 'degraded'
  database: 'healthy' | 'unavailable'
  checked_at: string
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl}/api/v1/health`, {
    headers: { Accept: 'application/json' },
    signal,
  })

  if (!response.ok) {
    throw new Error(`Backend health request failed (${response.status})`)
  }

  return (await response.json()) as HealthResponse
}
