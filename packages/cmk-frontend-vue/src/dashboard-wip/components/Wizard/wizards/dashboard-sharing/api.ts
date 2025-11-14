/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

import client, { unwrap } from '@/lib/rest-api-client/client'

type CreateDashboardToken = components['schemas']['CreateDashboardToken']
type EditDashboardToken = components['schemas']['EditDashboardToken']
type DeleteDashboardToken = components['schemas']['DeleteDashboardToken']
export type DashboardTokenModel = components['schemas']['DashboardTokenModel']

const CONTENT_TYPE_HEADER = {
  params: {
    header: { 'Content-Type': 'application/json' }
  }
}

export const createToken = async (
  dashboardId: string,
  dashboardOwner: string,
  expiresAt?: Date | null | undefined,
  comment?: string | null | undefined
): Promise<DashboardTokenModel> => {
  const payload: CreateDashboardToken = {
    dashboard_id: dashboardId,
    dashboard_owner: dashboardOwner,
    comment: comment || ''
  }

  if (expiresAt) {
    payload.expires_at = expiresAt.toISOString()
  }

  const resp = await client.POST('/domain-types/dashboard_token/collections/all', {
    ...CONTENT_TYPE_HEADER,
    body: payload
  })

  const tokenResp = unwrap(resp)
  return {
    ...tokenResp.extensions,
    token_id: tokenResp.id!
  }
}

export const updateToken = async (
  dashboardId: string,
  dashboardOwner: string,
  isDisabled: boolean | undefined,
  expiresAt: Date,
  comment: string | null | undefined
): Promise<DashboardTokenModel> => {
  const payload: EditDashboardToken = {
    dashboard_id: dashboardId,
    dashboard_owner: dashboardOwner,
    is_disabled: isDisabled || false,
    expires_at: expiresAt.toISOString(),
    comment: comment || ''
  }

  const resp = await client.POST('/domain-types/dashboard_token/actions/edit/invoke', {
    ...CONTENT_TYPE_HEADER,
    body: payload
  })

  const tokenResp = unwrap(resp)
  return {
    ...tokenResp.extensions,
    token_id: tokenResp.id!
  }
}

export const deleteToken = async (dashboardId: string, dashboardOwner: string) => {
  const payload: DeleteDashboardToken = {
    dashboard_id: dashboardId,
    dashboard_owner: dashboardOwner
  }

  await client.POST('/domain-types/dashboard_token/actions/delete/invoke', {
    ...CONTENT_TYPE_HEADER,
    body: payload
  })
}
