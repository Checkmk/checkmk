/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The handshake that turns the surrounding Checkmk session into a daemon credential.
 *
 * The SPA runs inside Checkmk, so the user is already authenticated (2FA
 * included). The ticket endpoint mints a short-lived signed ticket plus the
 * caller's resolved capabilities; that ticket is what the daemon accepts. There
 * is no login, refresh or user management of the SPA's own.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

/**
 * What the ticket grants, straight off the endpoint's own schema — including
 * which verbs it can carry, so a button gated on one cannot outlive the verb.
 */
export type MapsCapabilities = components['schemas']['MapsTicketCapabilities']

export type CommandVerb = MapsCapabilities['commands'][number]

/**
 * What the handshake answers. ``stream_token`` is the reduced-capability,
 * map-bound token for the event-stream URL: ``EventSource`` cannot set headers,
 * so that credential rides the query string, where it can reach an access log —
 * hence its own audience, which the daemon rejects everywhere else. It is there
 * only for a map-scoped ticket; the map list opens no stream.
 */
export type MapsTicket = components['schemas']['MapsTicketResponse']

export class TicketApi {
  /**
   * Mints a ticket, scoped to ``mapName`` when a map is open.
   *
   * The scope is what lets the daemon key its shared broadcast loop by the map's
   * real owner instead of by the viewer, so every viewer of a published map
   * shares one Livestatus poll.
   */
  public async fetchTicket(mapName?: string): Promise<MapsTicket> {
    return unwrap(
      await client.GET('/domain-types/maps_ticket/collections/all', {
        ...(mapName === undefined ? {} : { params: { query: { name: mapName } } })
      })
    )
  }
}

/** Where to send a caller whose Checkmk session ended, and back afterwards. */
export function checkmkLoginUrl(): string {
  const url = new URL('login.py', window.location.href)
  url.searchParams.set('_origtarget', window.location.href)
  return url.href
}

export function checkmkLogoutUrl(): string {
  return new URL('logout.py', window.location.href).href
}
