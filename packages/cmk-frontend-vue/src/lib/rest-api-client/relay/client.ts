/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fetchRestAPI } from '@/lib/cmkFetch'

export interface Relay {
  id: string
  alias: string
  siteid: string
  num_fetchers: number
  log_level: string
}

interface ApiRelay {
  id: string
  extensions?: {
    alias?: string
    siteid?: string
    num_fetchers?: number
    log_level?: string
  }
}
/**
 * Fetches all relay collections from the REST API.
 * Throws on HTTP error.
 * Returns array of relays (may be empty).
 */
export async function getRelayCollection(): Promise<Relay[]> {
  const API_ROOT = 'api/1.0'
  const url = `${API_ROOT}/domain-types/relay/collections/all`
  const response = await fetchRestAPI(url, 'GET')
  await response.raiseForStatus()
  const data = await response.json()

  if (!Array.isArray(data.value)) {
    return []
  }
  return (data.value as ApiRelay[]).map((relay) => ({
    id: relay.id,
    alias: relay.extensions?.alias ?? '',
    siteid: relay.extensions?.siteid ?? '',
    num_fetchers: relay.extensions?.num_fetchers ?? 0,
    log_level: relay.extensions?.log_level ?? ''
  }))
}
