/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The Maps daemon's client.
 *
 * The other server the SPA talks to is Checkmk itself, reached through the
 * shared ``lib/rest-api-client`` and its generated types — imported where it is
 * used, because it needs no wiring. The daemon client does: it carries the
 * caller's ticket.
 */
import type { paths } from 'cmk-shared-typing/typescript/maps_openapi'
import { type DaemonAuth, createDaemonClient } from 'cmk-ui-library/lib/daemon-client/client'

import { resolveDaemonBase } from '@/maps/utils/deploymentBase'

export type MapsDaemonClient = ReturnType<typeof createDaemonClient<paths>>

/**
 * A client for the Maps daemon.
 *
 * Created per app rather than imported as a module singleton: it carries the
 * caller's credential through the auth hook, and that is owned by a service with
 * the app's lifetime, not by the module.
 */
export function createMapsDaemonClient(auth: DaemonAuth): MapsDaemonClient {
  return createDaemonClient<paths>({ baseUrl: resolveDaemonBase(), auth })
}
