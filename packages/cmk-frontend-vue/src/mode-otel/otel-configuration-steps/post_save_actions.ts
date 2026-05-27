/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkFetchError, fetchRestAPI } from '@/lib/cmkFetch.ts'
import usei18n from '@/lib/i18n'

import { configEntityAPI } from '@/form/configuration_entity'

import type { EventConsoleConfig } from './otelTypes'
import type { PasswordConfig } from './password_store_password.types.ts'

const { _t } = usei18n()

/**
 * Standard REST API object endpoints (password, folder) enforce ETag locking:
 * a DELETE without an `If-Match` header is rejected with 428 Precondition
 * Required. Since rollbacks delete objects this run just created, there is no
 * concurrent-modification concern — send the star tag to satisfy the
 * precondition without a preceding GET. (Internal otel endpoints ignore it.)
 */
const IF_MATCH_ANY = { 'If-Match': '*' }

const OTEL_RECEIVERS_COLLECTION =
  'api/internal/domain-types/otel_collector_config_receivers/collections/all'
const PROM_SCRAPE_COLLECTION =
  'api/internal/domain-types/otel_collector_config_prom_scrape/collections/all'
const OTEL_BUNDLES_COLLECTION =
  'api/internal/domain-types/otel_collector_config_bundles/collections/all'

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
 * to the user inline next to the corresponding checklist item. On success,
 * an optional `rollback` closure is returned that undoes the action — used
 * by FinalizeConfiguration to revert previously completed steps when a
 * later action fails.
 */
export type PostSaveResult =
  | { ok: true; rollback?: () => Promise<void> }
  | { ok: false; error: { title: string; detail: string } }

/** The failure variant of {@link PostSaveResult}. */
type PostSaveError = Extract<PostSaveResult, { ok: false }>

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
  /**
   * When true the action still runs in sequence with the others but is not
   * shown as a checklist row. Errors still surface via the alert box.
   */
  hidden?: boolean
}

export function errorFromUnknown(err: unknown, fallbackTitle: string): PostSaveError {
  // Only CmkFetchError carries a useful server-side detail; every other
  // failure (network error, JS throw, …) shows the title alone.
  if (err instanceof CmkFetchError) {
    // CmkFetchError.message is `"${httpStatusPhrase}: ${apiDetail}"` — strip
    // the HTTP phrase and keep only the REST API detail sentence.
    const colonIndex = err.message.indexOf(': ')
    const detail = colonIndex > 0 ? err.message.slice(colonIndex + 2) : err.message
    return { ok: false, error: { title: fallbackTitle, detail } }
  }
  return { ok: false, error: { title: fallbackTitle, detail: '' } }
}

/**
 * Returns whether the OTel collector is currently enabled for a site.
 * Throws on network or server errors so the calling action can fail cleanly
 * before any mutation is made.
 */
async function isCollectorEnabled(siteId: string): Promise<boolean> {
  const response = await fetchRestAPI(
    `api/internal/domain-types/otel_collector/actions/get/invoke?site_id=${encodeURIComponent(siteId)}`,
    'GET'
  )
  await response.raiseForStatus()
  const body = (await response.json()) as { activation: { mode: string } }
  return body.activation.mode === 'enabled'
}

/**
 * Returns whether the metric backend is currently enabled for a site.
 * Throws on network or server errors so the calling action can fail cleanly
 * before any mutation is made.
 */
async function isMetricBackendEnabled(siteId: string): Promise<boolean> {
  const response = await fetchRestAPI(
    `api/internal/domain-types/metric_backend/actions/get/invoke?site_id=${encodeURIComponent(siteId)}`,
    'GET'
  )
  await response.raiseForStatus()
  const body = (await response.json()) as { type: string }
  return body.type === 'enabled'
}

/**
 * If the POST fails for any reason we verify the folder exists via GET before
 * surfacing the error — a 200 on the GET means the folder is already there and
 * we can proceed. This action must run before createDCDConnectorAction because
 * the DCD endpoint validates that the folder path exists.
 */

async function createTelemetryFolderAction(): Promise<PostSaveResult> {
  const deleteFolder = async () => {
    // The folder_config DELETE endpoint enforces ETag locking — see IF_MATCH_ANY.
    await fetchRestAPI(
      'api/1.0/objects/folder_config/~telemetry',
      'DELETE',
      undefined,
      IF_MATCH_ANY
    )
  }
  try {
    const response = await fetchRestAPI(
      'api/1.0/domain-types/folder_config/collections/all',
      'POST',
      { title: 'Telemetry', parent: '/', name: 'telemetry' }
    )
    if (response.status >= 200 && response.status <= 299) {
      return { ok: true, rollback: deleteFolder }
    }
    // POST failed — the folder may already exist. Check the actual state
    // instead of parsing the error body.
    const check = await fetchRestAPI('api/1.0/objects/folder_config/~telemetry', 'GET')
    if (check.status === 200) {
      // Pre-existing folder: succeed, but without a rollback so we never delete
      // a folder this run did not create.
      return { ok: true }
    }
    await response.raiseForStatus()
    return { ok: true }
  } catch (err) {
    return errorFromUnknown(err, _t('Could not create the Telemetry hosts folder'))
  }
}

async function createDCDConnector(ctx: PostSaveContext): Promise<PostSaveResult> {
  try {
    const dcdId = `quick_setup_${ctx.configName}`
    const response = await fetchRestAPI(
      'api/internal/domain-types/dcd_metric_backend/collections/all',
      'POST',
      {
        title: ctx.configName,
        site: ctx.siteId,
        dcd_id: dcdId,
        connector: {
          connector_type: 'metric_backend',
          host_name_template: '$RESOURCE_ATTR.service.name$',
          creation_rules: [{ folder_path: '/telemetry', delete_hosts: true }]
        }
      }
    )
    if (response.status === 409) {
      return { ok: true }
    }
    await response.raiseForStatus()
    return {
      ok: true,
      rollback: async () => {
        await fetchRestAPI(
          `api/internal/objects/dcd_metric_backend/${encodeURIComponent(dcdId)}`,
          'DELETE'
        )
      }
    }
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
export const createDCDConnectorAction: PostSaveAction = {
  key: 'createDCDConnector',
  label: () => _t('Dynamic host management setup'),
  execute: async (ctx) => {
    const folderResult = await createTelemetryFolderAction()
    if (!folderResult.ok) {
      return folderResult
    }
    const dcdResult = await createDCDConnector(ctx)
    if (!dcdResult.ok) {
      // DCD failed after the folder was created — roll the folder back immediately
      // since the state machine only calls rollbacks for actions that succeeded.
      await folderResult.rollback?.()
      return dcdResult
    }
    // Both succeeded — combine into one rollback: DCD first (it references the
    // folder), folder second.
    const { rollback: rollbackDcd } = dcdResult
    const { rollback: rollbackFolder } = folderResult
    if (!rollbackDcd && !rollbackFolder) {
      return { ok: true }
    }
    return {
      ok: true,
      rollback: async () => {
        await rollbackDcd?.()
        await rollbackFolder?.()
      }
    }
  }
}

/**
 * Action: enable the OpenTelemetry collector for the selected site.
 *
 * Checks the current collector state first so that rollback only disables it
 * if it was disabled before this save operation — preventing an unintended
 * side-effect on an already-enabled collector.
 */
export const enableCollectorAction: PostSaveAction = {
  key: 'enableCollector',
  label: () => _t('OpenTelemetry Collector activation'),
  execute: async (ctx) => {
    try {
      const wasEnabled = await isCollectorEnabled(ctx.siteId)
      const response = await fetchRestAPI(
        'api/internal/domain-types/otel_collector/actions/update/invoke',
        'PUT',
        {
          site_id: ctx.siteId,
          activation: { mode: 'enabled' }
        }
      )
      await response.raiseForStatus()
      if (wasEnabled) {
        return { ok: true }
      }
      return {
        ok: true,
        rollback: async () => {
          await fetchRestAPI(
            'api/internal/domain-types/otel_collector/actions/update/invoke',
            'PUT',
            { site_id: ctx.siteId, activation: { mode: 'disabled' } }
          )
        }
      }
    } catch (err) {
      return errorFromUnknown(err, _t('Could not enable the OpenTelemetry Collector'))
    }
  }
}

/**
 * Action: enable the metric backend (ClickHouse) for the selected site.
 *
 * Checks the current metric backend state first so that rollback only disables
 * it if it was disabled before this save operation — preventing an unintended
 * side-effect on an already-enabled metric backend.
 */
export const enableMetricBackendAction: PostSaveAction = {
  key: 'enableMetricBackend',
  label: () => _t('Metric backend connection'),
  execute: async (ctx) => {
    try {
      const wasEnabled = await isMetricBackendEnabled(ctx.siteId)
      const response = await fetchRestAPI(
        'api/internal/domain-types/metric_backend/actions/update/invoke',
        'PATCH',
        {
          site_id: ctx.siteId,
          config: { type: 'enabled' }
        }
      )
      await response.raiseForStatus()
      if (wasEnabled) {
        return { ok: true }
      }
      return {
        ok: true,
        rollback: async () => {
          await fetchRestAPI(
            'api/internal/domain-types/metric_backend/actions/update/invoke',
            'PATCH',
            { site_id: ctx.siteId, config: { type: 'disabled' } }
          )
        }
      }
    } catch (err) {
      return errorFromUnknown(err, _t('Could not enable the metric backend'))
    }
  }
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
  /** Password-store entries referenced by the auth payload. Saved and rolled back together with the receiver config. */
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
 * Deletes password-store entries created during this QuickSetup run. The
 * password DELETE endpoint enforces ETag locking, so the star tag satisfies
 * the precondition (see IF_MATCH_ANY).
 */
function deletePasswords(ids: readonly string[]): Promise<unknown> {
  return Promise.all(
    ids.map((id) =>
      fetchRestAPI(
        `api/1.0/objects/password/${encodeURIComponent(id)}`,
        'DELETE',
        undefined,
        IF_MATCH_ANY
      )
    )
  )
}

/**
 * Persists the password-store entries referenced by the receiver auth payload;
 * they must exist before the receiver POST embeds their IDs as
 * `{ type: 'store', value: <id> }`, which the server rejects if unknown.
 *
 * Returns the created IDs so the caller can delete them on rollback. On the
 * first failure the entries created so far are removed first. `createEntity`
 * reports only HTTP 422 as a structured error; any other failure throws and is
 * converted via errorFromUnknown.
 */
async function saveReceiverPasswords(
  passwords: readonly PasswordConfig[]
): Promise<{ ok: true; createdIds: string[] } | PostSaveError> {
  const createdIds: string[] = []
  for (const config of passwords) {
    try {
      const result = await configEntityAPI.createEntity(
        'passwordstore_password',
        'passwordstore_password',
        config
      )
      if (result.type === 'error') {
        await deletePasswords(createdIds)
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
      createdIds.push(config.general_props.id)
    } catch (err) {
      await deletePasswords(createdIds)
      return errorFromUnknown(err, _t('Could not save the referenced passwords'))
    }
  }
  return { ok: true, createdIds }
}

/**
 * Builds the `otel_collector_config_receivers` POST body. The wizard's single
 * configuration name doubles as both the id and the Overview display title.
 */
function buildReceiverBody(input: OTelReceiverConfigInput): Record<string, unknown> {
  const body: Record<string, unknown> = {
    id: input.id,
    title: input.id,
    disabled: false,
    site: [input.siteId]
  }
  if (input.grpc) {
    body['receiver_protocol_grpc'] = buildProtocolBody(input.grpc)
  }
  if (input.http) {
    body['receiver_protocol_http'] = buildProtocolBody(input.http)
  }
  return body
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
      const saved = await saveReceiverPasswords(input.passwords)
      if (!saved.ok) {
        return saved
      }
      const { createdIds } = saved
      try {
        const response = await fetchRestAPI(
          OTEL_RECEIVERS_COLLECTION,
          'POST',
          buildReceiverBody(input)
        )
        await response.raiseForStatus()
        return {
          ok: true,
          rollback: async () => {
            await fetchRestAPI(
              `api/internal/objects/otel_collector_config_receivers/${encodeURIComponent(input.id)}`,
              'DELETE'
            )
            await deletePasswords(createdIds)
          }
        }
      } catch (err) {
        // Passwords were created but the receiver POST failed — undo them.
        await deletePasswords(createdIds)
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
        return {
          ok: true,
          rollback: async () => {
            await fetchRestAPI(
              `api/internal/objects/otel_collector_config_prom_scrape/${encodeURIComponent(input.id)}`,
              'DELETE'
            )
          }
        }
      } catch (err) {
        return errorFromUnknown(err, _t('Could not create the Prometheus scraper configuration'))
      }
    }
  }
}

export interface OTelBundleInput {
  configName: string
  siteId: string
  passwordIds: string[]
}

/**
 * Factory: builds the create-OTel-bundle action that locks the receiver/prom-scrape config,
 * DCD connection, and any newly created passwords to a single QuickSetup configuration bundle.
 * Must run after all other post-save actions so the configs it references already exist.
 * Idempotent: if a bundle already exists for this config the backend returns the existing one.
 */
export function createOTelBundleAction(input: OTelBundleInput): PostSaveAction {
  return {
    key: 'createOTelBundle',
    label: () => _t('Configuration bundle setup'),
    hidden: true,
    execute: async () => {
      try {
        const response = await fetchRestAPI(OTEL_BUNDLES_COLLECTION, 'POST', {
          title: input.configName,
          site: input.siteId,
          otel_config_id: input.configName,
          dcd_connection_id: `quick_setup_${input.configName}`,
          password_ids: input.passwordIds
        })
        await response.raiseForStatus()
        const body = (await response.json()) as { extensions?: { bundle_id?: string } }
        const bundleId = body.extensions?.bundle_id
        if (!bundleId) {
          return { ok: true }
        }
        return {
          ok: true,
          rollback: async () => {
            await fetchRestAPI(
              `api/internal/objects/otel_collector_config_bundles/${encodeURIComponent(bundleId)}`,
              'DELETE'
            )
          }
        }
      } catch (err) {
        return errorFromUnknown(err, _t('Could not create the configuration bundle'))
      }
    }
  }
}

/**
 * Shared verify-and-add-change steps used by the OTel wizard, which builds
 * its final list as `[createReceiverConfigAction(...), ...POST_SAVE_ACTIONS]`
 * and filters per edition (cloud strips collector activation / metric
 * backend). The Prometheus wizard does not consume this list directly — it
 * composes its own ordered list via `buildPrometheusFinalizeActions`.
 */
export const POST_SAVE_ACTIONS: readonly PostSaveAction[] = [
  enableCollectorAction,
  enableMetricBackendAction,
  createDCDConnectorAction
]

/**
 * Builds the Prometheus QuickSetup finalize action list in the order the
 * checklist should display: collector on → backend on → scraper configured →
 * hosts auto-managed → bundle locked. Centralized here so the order is
 * testable without mounting the wizard component.
 */
export function buildPrometheusFinalizeActions(
  input: PrometheusScrapeConfigInput
): readonly PostSaveAction[] {
  return [
    enableCollectorAction,
    enableMetricBackendAction,
    createPrometheusScrapeConfigAction(input),
    createDCDConnectorAction,
    createOTelBundleAction({ configName: input.id, siteId: input.siteId, passwordIds: [] })
  ]
}
