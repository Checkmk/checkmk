/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Who is logged in and what they may do in Maps.
 *
 * The SPA runs inside Checkmk, so the user is already authenticated (2FA
 * included). The browser sends the GUI session cookie to the daemon too, and the
 * daemon has the GUI check it, so the SPA carries no credential of its own.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

/**
 * What the user may do, straight off the endpoint's own schema — including
 * which verbs they may send, so a button gated on one cannot outlive the verb.
 */
export type MapsCapabilities = components['schemas']['MapsCapabilities']

export type CommandVerb = MapsCapabilities['commands'][number]

export type MapsSession = components['schemas']['MapsSessionResponse']

export class SessionApi {
  public async fetchSession(): Promise<MapsSession> {
    return unwrap(await client.GET('/domain-types/maps_session/collections/all'))
  }
}

export function checkmkLoginUrl(): string {
  const url = new URL('login.py', window.location.href)
  url.searchParams.set('_origtarget', window.location.href)
  return url.href
}

export function checkmkLogoutUrl(): string {
  return new URL('logout.py', window.location.href).href
}
