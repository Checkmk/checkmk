/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import {
  type AlertExtensions,
  type AlertModel,
  type FolderPaths,
  type PredictionPeriods,
  alertConditions,
  alertName,
  alertThresholds,
  servicePattern
} from '@/mode-alerts/types'

export type SaveResult = { ok: true } | { ok: false; error: string }

export type LoadResult =
  | { ok: true; extensions: AlertExtensions; etag: string }
  | { ok: false; error: string }

function isClientError(error: unknown): error is CmkApiError {
  return error instanceof CmkApiError && error.statusCode < 500
}

function slugForId(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
}

export async function createAlert(
  model: AlertModel,
  folderPaths: FolderPaths,
  predictionPeriods: PredictionPeriods
): Promise<SaveResult> {
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
          service_match: { mode: model.matchType, pattern: servicePattern(model) },
          conditions: alertConditions(model, folderPaths),
          thresholds: alertThresholds(model, predictionPeriods)
        }
      })
    )
    return { ok: true }
  } catch (error) {
    if (isClientError(error)) {
      return { ok: false, error: error.message }
    }
    throw error
  }
}

export async function loadAlert(configurationName: string): Promise<LoadResult> {
  try {
    const result = await client.GET('/objects/telemetry_alert/{configuration_name}', {
      params: { path: { configuration_name: configurationName } }
    })
    const alert = unwrap(result)
    const etag = result.response.headers.get('ETag')
    // The endpoint always sends one; without it a later update could not detect a concurrent
    // change. Reported like a refusal, so the wizard shows why it cannot edit the alert.
    if (etag === null) {
      return {
        ok: false,
        error:
          'The server answered without a version identifier for this alert. Reload the page to load it again.'
      }
    }
    return { ok: true, extensions: alert.extensions, etag }
  } catch (error) {
    if (isClientError(error)) {
      return { ok: false, error: error.message }
    }
    throw error
  }
}

// The alert name is not sent: the update endpoint keeps the one the alert was created with.
export async function updateAlert(
  configurationName: string,
  model: AlertModel,
  folderPaths: FolderPaths,
  predictionPeriods: PredictionPeriods,
  etag: string
): Promise<SaveResult> {
  try {
    unwrap(
      await client.PUT('/objects/telemetry_alert/{configuration_name}', {
        params: {
          path: { configuration_name: configurationName },
          header: { 'Content-Type': 'application/json', 'If-Match': etag }
        },
        body: {
          service_match: { mode: model.matchType, pattern: servicePattern(model) },
          conditions: alertConditions(model, folderPaths),
          thresholds: alertThresholds(model, predictionPeriods)
        }
      })
    )
    return { ok: true }
  } catch (error) {
    if (isClientError(error)) {
      return { ok: false, error: error.message }
    }
    throw error
  }
}
