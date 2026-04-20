/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fetchRestAPI } from '@/lib/cmkFetch.ts'
import usei18n from '@/lib/i18n'

const { _t } = usei18n()

/**
 * Context handed to each post-save action. Holds values collected by the
 * QuickSetup steps that the actions may need to apply their change.
 */
export interface PostSaveContext {
  siteId: string
  configName: string
}

/**
 * Result returned by a PostSaveAction. On failure the `error` is surfaced
 * to the user inline next to the corresponding checklist item.
 */
export type PostSaveResult = { ok: true } | { ok: false; error: { title: string; detail: string } }

/**
 * A single verify-and-add-change step executed when the user finishes the
 * OpenTelemetry QuickSetup. New post-save steps are added by appending an
 * entry to the registry below — no other code needs to change.
 */
export interface PostSaveAction {
  /** Stable identifier used as the Vue key in the checklist. */
  key: string
  /**
   * Label shown to the user in the checklist. Called lazily so i18n lookups
   * happen at render time rather than module-eval time.
   */
  label: () => string
  /** Executes the action against the Checkmk REST API. */
  execute: (ctx: PostSaveContext) => Promise<PostSaveResult>
}

function errorFromUnknown(err: unknown, fallbackTitle: string): PostSaveResult {
  // REST API errors (CmkFetchError) surface a well-formed `{ title, detail }`
  // in the JSON body; generic network errors don't.
  if (err instanceof Error) {
    const msg = err.message || fallbackTitle
    // `${title}: ${detail}` is the shape CmkFetchError builds — split it back
    // so the UI can render title and detail separately.
    const colonIndex = msg.indexOf(': ')
    if (colonIndex > 0) {
      return {
        ok: false,
        error: { title: msg.slice(0, colonIndex), detail: msg.slice(colonIndex + 2) }
      }
    }
    return { ok: false, error: { title: fallbackTitle, detail: msg } }
  }
  return { ok: false, error: { title: fallbackTitle, detail: String(err) } }
}

/**
 * Action: create the "Telemetry" folder under the root folder.
 *
 * If the POST fails for any reason we verify the folder exists via GET before
 * surfacing the error — a 200 on the GET means the folder is already there and
 * we can proceed. This action must run before createDCDConnectorAction because
 * the DCD endpoint validates that the folder path exists.
 */
const createTelemetryFolderAction: PostSaveAction = {
  key: 'createTelemetryFolder',
  label: () => _t('Create Telemetry hosts folder'),
  execute: async (_ctx) => {
    try {
      const response = await fetchRestAPI(
        'api/1.0/domain-types/folder_config/collections/all',
        'POST',
        { title: 'Telemetry', parent: '/', name: 'telemetry' }
      )
      if (response.status >= 200 && response.status <= 299) {
        return { ok: true }
      }
      // POST didn't succeed — maybe the folder already exists, maybe something else went wrong.
      // Check the actual state instead of parsing the error body.
      const check = await fetchRestAPI('api/1.0/objects/folder_config/~telemetry', 'GET')
      if (check.status === 200) {
        return { ok: true }
      }
      // Folder really isn't there — the POST error is the real failure.
      await response.raiseForStatus()
      return { ok: true }
    } catch (err) {
      return errorFromUnknown(err, _t('Could not create the Telemetry hosts folder'))
    }
  }
}

/**
 * Action: create the "Telemetry" DCD metric backend connector.
 *
 * Uses `service.name` as the hostname resource attribute and creates hosts in
 * the "/telemetry" folder (created by createTelemetryFolderAction). The DCD ID
 * is derived from the config name so it is stable across wizard reruns. A 409
 * Conflict means the connector already exists and can be reused, so it is
 * treated as success.
 */
const createDCDConnectorAction: PostSaveAction = {
  key: 'createDCDConnector',
  label: () => _t('Set up metric backend connector'),
  execute: async (ctx) => {
    try {
      const response = await fetchRestAPI(
        'api/internal/domain-types/dcd_metric_backend/collections/all',
        'POST',
        {
          title: ctx.configName,
          site: ctx.siteId,
          dcd_id: `quick_setup_${ctx.configName}`,
          connector: {
            connector_type: 'metric_backend',
            host_name_resource_attribute_key: 'service.name',
            creation_rules: [{ folder_path: '/telemetry', delete_hosts: true }]
          }
        }
      )
      if (response.status === 409) {
        return { ok: true }
      }
      await response.raiseForStatus()
      return { ok: true }
    } catch (err) {
      return errorFromUnknown(err, _t('Could not create the metric backend connector'))
    }
  }
}

/**
 * Action: enable the OpenTelemetry collector for the selected site.
 *
 * Hits the internal `otel_collector/actions/update/invoke` endpoint which
 * toggles the `site_opentelemetry_collector` config var and records an
 * activation change. Idempotent from the user's perspective: if the
 * collector is already enabled, the endpoint still returns 204 and the
 * resulting "change" collapses to a no-op on activation.
 */
const enableCollectorAction: PostSaveAction = {
  key: 'enableCollector',
  label: () => _t('OpenTelemetry Collector activation'),
  execute: async (ctx) => {
    try {
      const response = await fetchRestAPI(
        'api/internal/domain-types/otel_collector/actions/update/invoke',
        'PUT',
        {
          site_id: ctx.siteId,
          activation: { mode: 'enabled' }
        }
      )
      await response.raiseForStatus()
      return { ok: true }
    } catch (err) {
      return errorFromUnknown(err, _t('Could not enable the OpenTelemetry Collector'))
    }
  }
}

/**
 * Action: enable the metric backend (ClickHouse) for the selected site.
 *
 * Hits the internal `metric_backend/actions/update/invoke` endpoint which
 * configures and enables the metric backend with default port settings for
 * the site. Idempotent: if the backend is already enabled the endpoint
 * still returns 204 and the resulting "change" collapses to a no-op on
 * activation.
 */
const enableMetricBackendAction: PostSaveAction = {
  key: 'enableMetricBackend',
  label: () => _t('Metric backend connection'),
  execute: async (ctx) => {
    try {
      const response = await fetchRestAPI(
        'api/internal/domain-types/metric_backend/actions/update/invoke',
        'PATCH',
        {
          site_id: ctx.siteId,
          config: { type: 'enabled' }
        }
      )
      await response.raiseForStatus()
      return { ok: true }
    } catch (err) {
      return errorFromUnknown(err, _t('Could not enable the metric backend'))
    }
  }
}

/**
 * Ordered list of steps run by the QuickSetup finalize stage. To add a new
 * verify-and-add-change step append a new `PostSaveAction` here.
 */
export const POST_SAVE_ACTIONS: readonly PostSaveAction[] = [
  enableCollectorAction,
  enableMetricBackendAction,
  createTelemetryFolderAction,
  createDCDConnectorAction
]
