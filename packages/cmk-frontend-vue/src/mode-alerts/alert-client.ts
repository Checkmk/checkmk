/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import { type AlertModel, alertName, servicePattern } from '@/mode-alerts/types'

export type CreateResult = { ok: true } | { ok: false; error: string }

function slugForId(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
}

export async function createAlert(model: AlertModel): Promise<CreateResult> {
  const name = alertName(model)
  try {
    unwrap(
      await client.POST('/domain-types/telemetry_alert/collections/all', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: {
          // TODO: Replace the derived ID with a "Configuration name" field in the first step,
          // validated like the custom services one: required, ^[a-zA-Z_][a-zA-Z0-9_-]*$ (the
          // backend's REGEX_ID rejects a leading digit) and not taken. On a 409, show "A
          // configuration with this name already exists." instead of the backend's message.
          // Until then, "5xx rate too high" is rejected with a 400, and all names without
          // ASCII letters or digits share the ID "alert", so only the first one can be created.
          configuration_name: slugForId(name) || 'alert',
          alert_name: name,
          service_match: { mode: model.matchType, pattern: servicePattern(model) }
        }
      })
    )
    return { ok: true }
  } catch (error) {
    if (error instanceof CmkApiError && error.statusCode < 500) {
      return { ok: false, error: error.message }
    }
    throw error
  }
}
