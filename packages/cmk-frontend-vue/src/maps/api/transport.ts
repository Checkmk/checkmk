/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The Maps daemon's client.
 *
 * The other server the SPA talks to is Checkmk itself, reached through the
 * shared ``lib/rest-api-client`` and its generated types. Both are reached with
 * the GUI session cookie the browser sends anyway.
 */
import type { paths } from 'cmk-shared-typing/typescript/maps_openapi'
import { type FastApiClient, createFastApiClient } from 'cmk-ui-library/lib/fastapi-client/client'

import { resolveDaemonBase } from '@/maps/utils/deploymentBase'

export type MapsDaemonClient = FastApiClient<paths>

export function createMapsDaemonClient(): MapsDaemonClient {
  return createFastApiClient<paths>({ baseUrl: resolveDaemonBase() })
}
