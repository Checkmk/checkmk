/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import { restApiHttp } from 'cmk-ui-library/vitest.msw'

import { useRequestRecords } from '@tests/dashboard/apiHandlers'

type Schemas = components['schemas']

interface DashboardTokenRequests {
  created: Schemas['CreateDashboardToken'][]
  edited: Schemas['EditDashboardToken'][]
  deleted: Schemas['DeleteDashboardToken'][]
}

/** The token requests of the current test. */
export function useDashboardTokenRequests(): DashboardTokenRequests {
  return { created: useRequestRecords(), edited: useRequestRecords(), deleted: useRequestRecords() }
}

function tokenObject(
  isDisabled: boolean,
  comment: string,
  expiresAt: string | null
): Schemas['DashboardTokenObjectModel'] {
  return {
    domainType: 'dashboard_token',
    id: 'token',
    links: [],
    extensions: { is_disabled: isDisabled, issued_at: '', expires_at: expiresAt, comment }
  }
}

/** Serves the actions on the public token of a dashboard and records their requests. */
export function dashboardTokenHandlers(requests: DashboardTokenRequests) {
  return [
    restApiHttp.post(
      '/domain-types/dashboard_token/collections/all',
      async ({ request, response }) => {
        const body = await request.json()
        requests.created.push(body)
        return response(200).json(tokenObject(false, body.comment, body.expires_at ?? null))
      }
    ),
    restApiHttp.post(
      '/domain-types/dashboard_token/actions/edit/invoke',
      async ({ request, response }) => {
        const body = await request.json()
        requests.edited.push(body)
        return response(200).json(tokenObject(body.is_disabled, body.comment, body.expires_at))
      }
    ),
    restApiHttp.post(
      '/domain-types/dashboard_token/actions/delete/invoke',
      async ({ request, response }) => {
        requests.deleted.push(await request.json())
        return response(204).empty()
      }
    )
  ]
}
