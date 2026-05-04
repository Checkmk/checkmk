/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fetchRestAPI } from '@/lib/cmkFetch.ts'
import usei18n from '@/lib/i18n'

import { configEntityAPI } from '@/components/user-input/CmkConfigurationEntityDropdown'

import type { EventConsoleConfig } from './otelTypes'
import type { PasswordConfig } from './password_store_password.types.ts'

const { _t } = usei18n()

const OTEL_RECEIVERS_COLLECTION =
  'api/internal/domain-types/otel_collector_config_receivers/collections/all'
const PROM_SCRAPE_COLLECTION =
  'api/internal/domain-types/otel_collector_config_prom_scrape/collections/all'

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
 * If the POST fails for any reason we verify the folder exists via GET before
 * surfacing the error — a 200 on the GET means the folder is already there and
 * we can proceed. This action must run before createDCDConnectorAction because
 * the DCD endpoint validates that the folder path exists.
 */

async function createTelemetryFolderAction(): Promise<PostSaveResult> {
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

async function createDCDConnector(ctx: PostSaveContext): Promise<PostSaveResult> {
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
  label: () => _t('Dynamic host management setup'),
  execute: async (ctx) => {
    const folderResult = await createTelemetryFolderAction()
    if (!folderResult.ok) {
      return folderResult
    }
    return await createDCDConnector(ctx)
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
 * Persists each pending password via the slide-in schema and stops on the
 * first server rejection so the caller sees exactly which password failed.
 * Returned as a `PostSaveResult` so it can short-circuit the surrounding
 * receiver-config action without surfacing a separate checklist item.
 */
async function savePendingPasswords(passwords: readonly PasswordConfig[]): Promise<PostSaveResult> {
  for (const config of passwords) {
    const result = await configEntityAPI.createEntity(
      'passwordstore_password',
      'passwordstore_password',
      config as unknown as Record<string, unknown>
    )
    if (result.type === 'error') {
      const firstMessage = result.validationMessages[0]
      return {
        ok: false,
        error: {
          title: _t('Could not save password "%{title}"', {
            title: config.general_props.title
          }),
          detail: firstMessage?.message ?? _t('The password was rejected by the server.')
        }
      }
    }
  }
  return { ok: true }
}

/**
 * REST body shape for the `otel_collector_config_receivers` POST. The same URL
 * serves both the ultimate and cloud editions — the server picks the right
 * handler by edition, and only the body shape differs (cloud has no
 * address/port/encryption/event_console, only auth).
 */
type OTelAuthBody =
  | { type: 'none' }
  | {
      type: 'basicauth'
      userlist: { username: string; password: { type: 'store'; value: string } }[]
    }

type OTelSocketAddressBody =
  | { type: 'default_ipv4' }
  | { type: 'default_ipv6' }
  | { type: 'custom'; address: string; port: number }

type OTelEndpointBody =
  | { auth: OTelAuthBody }
  | {
      auth: OTelAuthBody
      socket_address: OTelSocketAddressBody
      encryption: boolean
      event_console: { host_name_resource_attribute_key: string } | null
    }

type OTelProtocolConfigBody = { endpoint: OTelEndpointBody }

/**
 * Auth payload the wizard hands to the create action. Discriminated on
 * `method`: `'basicauth'` carries non-nullable username + password-store id,
 * so the create action no longer needs runtime guards or empty-string
 * fallbacks. The wizard narrows `AuthConfig` (which allows nulls for
 * incomplete form state) into this shape at the boundary.
 */
export type OTelAuthInput =
  | { method: 'none' }
  | { method: 'basicauth'; username: string; passwordId: string }

/**
 * Socket-address payload the wizard hands to the create action. Discriminated
 * on `type`: `'custom'` carries a non-nullable port so the create action does
 * not have to fall back to `0`. The wizard narrows `EndpointConfig` (which
 * allows `port: undefined` for default modes) into this shape at the boundary.
 */
export type OTelSocketAddressInput =
  | { type: 'default_ipv4' }
  | { type: 'default_ipv6' }
  | { type: 'custom'; address: string; port: number }

/**
 * Per-protocol input the OTel wizard hands to the create action. One of these
 * is built for each tab (grpc, http); `null` means the user did not configure
 * that tab so the payload should omit the protocol entirely.
 */
export interface OTelReceiverProtocolInput {
  auth: OTelAuthInput
  /**
   * Socket address + encryption + event-console settings. Only collected on
   * editions that expose those fields in the UI (ultimate); omit on cloud.
   */
  extended?: {
    socketAddress: OTelSocketAddressInput
    encryption: boolean
    eventConsole: EventConsoleConfig | null
  }
}

export interface OTelReceiverConfigInput {
  id: string
  siteId: string
  grpc: OTelReceiverProtocolInput | null
  http: OTelReceiverProtocolInput | null
  /**
   * Password-store entries referenced by the auth payload that must be
   * persisted before the receiver POST — the server rejects unknown IDs in
   * `{ type: 'store', value: <id> }`. Saved silently as a prerequisite of
   * this action so the user does not see a separate "Save passwords" step.
   */
  passwords: readonly PasswordConfig[]
}

function buildAuthBody(auth: OTelAuthInput): OTelAuthBody {
  switch (auth.method) {
    case 'none':
      return { type: 'none' }
    case 'basicauth':
      return {
        type: 'basicauth',
        userlist: [{ username: auth.username, password: { type: 'store', value: auth.passwordId } }]
      }
  }
}

// Mirrors the server's `SocketAddressDefault | SocketAddressCustom`
// discriminator (non-free/cmk-otel-collector/.../full/_models.py): default
// modes only carry the type; custom carries an explicit address + port. The
// input shape encodes this invariant — no runtime guards needed here.
function buildSocketAddressBody(socketAddress: OTelSocketAddressInput): OTelSocketAddressBody {
  switch (socketAddress.type) {
    case 'default_ipv4':
    case 'default_ipv6':
      return { type: socketAddress.type }
    case 'custom':
      return { type: 'custom', address: socketAddress.address, port: socketAddress.port }
  }
}

function buildProtocolBody(input: OTelReceiverProtocolInput): OTelProtocolConfigBody {
  const auth = buildAuthBody(input.auth)
  if (!input.extended) {
    return { endpoint: { auth } }
  }
  return {
    endpoint: {
      auth,
      socket_address: buildSocketAddressBody(input.extended.socketAddress),
      encryption: input.extended.encryption,
      event_console: input.extended.eventConsole
        ? { host_name_resource_attribute_key: input.extended.eventConsole.resourceAttribute }
        : null
    }
  }
}

/**
 * Factory: builds the create-OTel-receiver action for a single QuickSetup run.
 * Captures the user-entered config in a closure so `POST_SAVE_ACTIONS` can
 * stay a static list while this per-run action lives alongside.
 *
 * Hits the `otel_collector_config_receivers/collections/all` POST endpoint,
 * which is dispatched server-side to the ultimate or cloud handler based on
 * the active edition. If the POST fails the FinalizeConfiguration state
 * machine stops before the collector/metric-backend activation runs — that
 * is required by the "cannot finish if config creation fails" criterion.
 */
export function createOTelReceiverConfigAction(input: OTelReceiverConfigInput): PostSaveAction {
  return {
    key: 'createOTelReceiverConfig',
    label: () => _t('Collector configuration'),
    execute: async () => {
      // Passwords must land in the store before the receiver POST embeds
      // their IDs as `{ type: 'store', value: <id> }` references — the
      // server rejects unknown IDs. A failure here aborts the action with a
      // password-specific error so the user can fix the offending entry.
      const passwordResult = await savePendingPasswords(input.passwords)
      if (!passwordResult.ok) {
        return passwordResult
      }
      try {
        const body: Record<string, unknown> = {
          id: input.id,
          // The wizard collects a single "configuration name" that serves as
          // both the identifier and the display title in the Overview list.
          title: input.id,
          disabled: false,
          site: [input.siteId]
        }
        // Body building can throw (e.g. `buildSocketAddressBody` rejects a
        // custom socket address without a port); keep it inside the try so
        // the failure surfaces as a structured `PostSaveResult` instead of
        // an unhandled rejection.
        if (input.grpc) {
          body['receiver_protocol_grpc'] = buildProtocolBody(input.grpc)
        }
        if (input.http) {
          body['receiver_protocol_http'] = buildProtocolBody(input.http)
        }
        const response = await fetchRestAPI(OTEL_RECEIVERS_COLLECTION, 'POST', body)
        await response.raiseForStatus()
        return { ok: true }
      } catch (err) {
        return errorFromUnknown(
          err,
          _t('Could not create the OpenTelemetry Collector configuration')
        )
      }
    }
  }
}

export interface PrometheusScrapeConfigInput {
  id: string
  siteId: string
  jobName: string
  metricsPath: string
  address: string
  port: number
  encryption: boolean
}

/** Prometheus scrape_interval the wizard doesn't expose; mirrors the default
 * of many Prometheus deployments and can be edited on the detail page later. */
const PROM_DEFAULT_SCRAPE_INTERVAL_SECONDS = 60

/**
 * Factory: builds the create-Prometheus-scraper action for a single
 * QuickSetup run. Only the ultimate edition ships this endpoint (there is no
 * Prometheus Quick Setup on cloud), so no edition branching is needed.
 */
export function createPrometheusScrapeConfigAction(
  input: PrometheusScrapeConfigInput
): PostSaveAction {
  return {
    key: 'createPrometheusScrapeConfig',
    label: () => _t('Prometheus scraper configuration'),
    execute: async () => {
      const body = {
        id: input.id,
        // Mirrors the OTel create action: the wizard-level configuration name
        // is reused as the display title in the Prometheus Overview list.
        title: input.id,
        disabled: false,
        site: [input.siteId],
        prometheus_scrape_configs: [
          {
            job_name: input.jobName,
            scrape_interval: PROM_DEFAULT_SCRAPE_INTERVAL_SECONDS,
            metrics_path: input.metricsPath,
            targets: [{ address: input.address, port: input.port }],
            encryption: input.encryption
          }
        ]
      }
      try {
        const response = await fetchRestAPI(PROM_SCRAPE_COLLECTION, 'POST', body)
        await response.raiseForStatus()
        return { ok: true }
      } catch (err) {
        return errorFromUnknown(err, _t('Could not create the Prometheus scraper configuration'))
      }
    }
  }
}

/**
 * Shared verify-and-add-change steps that run after the wizard's per-run
 * create action. Wizards build their final action list as
 * `[createReceiverConfigAction(...), ...POST_SAVE_ACTIONS]`, filtering this
 * list per edition (cloud strips collector activation / metric backend).
 * Append new shared steps here.
 */
export const POST_SAVE_ACTIONS: readonly PostSaveAction[] = [
  enableCollectorAction,
  enableMetricBackendAction,
  createDCDConnectorAction
]
