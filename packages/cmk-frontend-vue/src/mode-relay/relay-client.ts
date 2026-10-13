/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

export interface Relay {
  id: string
  alias: string
  siteid: string
  num_fetchers: number
  log_level: string
}

/**
 * Fetches all relay collections from the REST API.
 * Throws on HTTP error.
 * Returns array of relays (may be empty).
 */
export async function getRelayCollection(): Promise<Relay[]> {
  const data = unwrap(await client.GET('/domain-types/relay/collections/all'))
  return data.value.map((relay) => ({
    id: relay.id!,
    alias: relay.extensions.alias,
    siteid: relay.extensions.siteid,
    num_fetchers: relay.extensions.num_fetchers,
    log_level: relay.extensions.log_level
  }))
}
