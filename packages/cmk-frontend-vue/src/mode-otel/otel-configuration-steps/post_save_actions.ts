/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import { CmkApiError } from 'cmk-ui-library/lib/error'
import usei18n from 'cmk-ui-library/lib/i18n'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import { configEntityAPI } from '@/form/configuration_entity'

import type { EventConsoleConfig } from './otelTypes'
import type { PasswordConfig } from './password_store_password.types.ts'

const { _t } = usei18n()

/**
 * Several REST API object DELETE endpoints enforce ETag locking: a DELETE
 * without an `If-Match` header is rejected with 428 Precondition Required. This
 * covers the standard password and folder endpoints as well as the internal
 * OTel collector receiver, Prometheus scrape config, and DCD telemetry metrics
 * endpoints. We send the star tag rather than a captured ETag because the Quick
 * Setup mutates these records after creating them — the configuration bundle
 * stamps `locked_by` on them, which is part of the hashed state — so an ETag
 * captured at creation is already stale by the time a rollback deletes the
 * record. The star tag matches any version. (The OTel bundle endpoint does not
 * enforce ETag locking, so its rollback omits the header.)
 */
const IF_MATCH_ANY = { 'If-Match': '*' }

const CONTENT_TYPE_JSON = { 'Content-Type': 'application/json' } as const

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
  // Only CmkApiError carries a useful server-side detail; every other
  // failure (network error, JS throw, …) shows the title alone.
  if (err instanceof CmkApiError) {
    // CmkApiError.message is `"${httpStatusPhrase}: ${apiDetail}"` — strip
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
  const body = unwrap(
    await client.GET('/domain-types/otel_collector/actions/get/invoke', {
      params: { query: { site_id: siteId } }
    })
  )
  return body.activation.mode === 'enabled'
}

/**
 * Returns whether the data backend is currently enabled for a site.
 * Throws on network or server errors so the calling action can fail cleanly
 * before any mutation is made.
 */
async function isDataBackendEnabled(siteId: string): Promise<boolean> {
  const body = unwrap(
    await client.GET('/domain-types/data_backend/actions/get/invoke', {
      params: { query: { site_id: siteId } }
    })
  )
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
    // Unlike the other ETag-locked DELETEs this one does not declare If-Match in
    // the spec, so it is sent as a plain request header rather than a typed param.
    await client.DELETE('/objects/folder_config/{folder}', {
      params: { path: { folder: '~telemetry' } },
      headers: IF_MATCH_ANY
    })
  }
  try {
    const result = await client.POST('/domain-types/folder_config/collections/all', {
      params: { header: CONTENT_TYPE_JSON },
      body: { title: 'Telemetry', parent: '/', name: 'telemetry' }
    })
    if (result.response.status >= 200 && result.response.status <= 299) {
      return { ok: true, rollback: deleteFolder }
    }
    // POST failed — the folder may already exist. Check the actual state
    // instead of parsing the error body.
    const check = await client.GET('/objects/folder_config/{folder}', {
      params: { path: { folder: '~telemetry' } }
    })
    if (check.response.status === 200) {
      // Pre-existing folder: succeed, but without a rollback so we never delete
      // a folder this run did not create.
      return { ok: true }
    }
    unwrap(result)
    return { ok: true }
  } catch (err) {
    return errorFromUnknown(err, _t('Could not create the Telemetry hosts folder'))
  }
}

async function createDCDConnector(ctx: PostSaveContext): Promise<PostSaveResult> {
  try {
    const dcdId = `quick_setup_${ctx.configName}`
    const result = await client.POST('/domain-types/dcd_telemetry_metrics/collections/all', {
      params: { header: CONTENT_TYPE_JSON },
      body: {
        title: ctx.configName,
        // openapi-typescript types a request field that carries a default as
        // required, so these have to be sent even though the server would
        // supply them. The values mirror the server-side defaults.
        comment: '',
        documentation_url: '',
        disabled: false,
        site: ctx.siteId,
        dcd_id: dcdId,
        connector: {
          connector_type: 'telemetry_metrics',
          interval: 60,
          discover_on_creation: true,
          validity_period: 3600,
          maximum_number_of_hosts: 500,
          host_name_lookup_rules: [{ host_name_template: '$RESOURCE_ATTR.service.name$' }],
          creation_rules: [{ folder_path: '/telemetry', delete_hosts: true }]
        }
      }
    })
    if (result.response.status === 409) {
      return { ok: true }
    }
    unwrap(result)
    return {
      ok: true,
      rollback: async () => {
        // The dcd_telemetry_metrics DELETE endpoint enforces ETag locking — see IF_MATCH_ANY.
        await client.DELETE('/objects/dcd_telemetry_metrics/{dcd_id}', {
          params: { header: IF_MATCH_ANY, path: { dcd_id: dcdId } }
        })
      }
    }
  } catch (err) {
    return errorFromUnknown(err, _t('Could not create the telemetry metrics connector'))
  }
}
/**
 * Action: create the "Telemetry" DCD telemetry metrics connector.
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
      unwrap(
        await client.PUT('/domain-types/otel_collector/actions/update/invoke', {
          params: { header: CONTENT_TYPE_JSON },
          body: { site_id: ctx.siteId, activation: { mode: 'enabled' } }
        })
      )
      if (wasEnabled) {
        return { ok: true }
      }
      return {
        ok: true,
        rollback: async () => {
          await client.PUT('/domain-types/otel_collector/actions/update/invoke', {
            params: { header: CONTENT_TYPE_JSON },
            body: { site_id: ctx.siteId, activation: { mode: 'disabled' } }
          })
        }
      }
    } catch (err) {
      return errorFromUnknown(err, _t('Could not enable the OpenTelemetry Collector'))
    }
  }
}

/**
 * Action: enable the data backend (ClickHouse) for the selected site.
 *
 * Checks the current data backend state first so that rollback only disables
 * it if it was disabled before this save operation — preventing an unintended
 * side-effect on an already-enabled data backend.
 */
export const enableDataBackendAction: PostSaveAction = {
  key: 'enableDataBackend',
  label: () => _t('Data backend connection'),
  execute: async (ctx) => {
    try {
      const wasEnabled = await isDataBackendEnabled(ctx.siteId)
      unwrap(
        await client.PATCH('/domain-types/data_backend/actions/update/invoke', {
          params: { header: CONTENT_TYPE_JSON },
          body: { site_id: ctx.siteId, config: { type: 'enabled' } }
        })
      )
      if (wasEnabled) {
        return { ok: true }
      }
      return {
        ok: true,
        rollback: async () => {
          await client.PATCH('/domain-types/data_backend/actions/update/invoke', {
            params: { header: CONTENT_TYPE_JSON },
            body: { site_id: ctx.siteId, config: { type: 'disabled' } }
          })
        }
      }
    } catch (err) {
      return errorFromUnknown(err, _t('Could not enable the data backend'))
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
      client.DELETE('/objects/password/{name}', {
        params: { header: IF_MATCH_ANY, path: { name: id } }
      })
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
 * Request body of the `otel_collector_config_receivers` POST. Declared here
 * rather than taken from the generated spec because the merged internal spec
 * describes only the ultimate shape — see the assertion at the call site. A
 * protocol key is omitted entirely when the user did not configure that tab.
 */
interface OTelReceiverBody {
  id: string
  title: string
  disabled: boolean
  site: string[]
  receiver_protocol_grpc?: OTelProtocolConfigBody
  receiver_protocol_http?: OTelProtocolConfigBody
}

/**
 * Builds the `otel_collector_config_receivers` POST body. The wizard's single
 * configuration name doubles as both the id and the Overview display title.
 */
function buildReceiverBody(input: OTelReceiverConfigInput): OTelReceiverBody {
  const body: OTelReceiverBody = {
    id: input.id,
    title: input.id,
    disabled: false,
    site: [input.siteId]
  }
  if (input.grpc) {
    body.receiver_protocol_grpc = buildProtocolBody(input.grpc)
  }
  if (input.http) {
    body.receiver_protocol_http = buildProtocolBody(input.http)
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
 * machine stops before the collector/data-backend activation runs — that
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
        unwrap(
          await client.POST('/domain-types/otel_collector_config_receivers/collections/all', {
            params: { header: CONTENT_TYPE_JSON },
            // The merged internal spec carries only the ultimate shape of
            // OTelCollectorProtocolConfig: merge_api_specs drops the cloud variant
            // (_KNOWN_DIVERGENT_COMPONENTS), whose endpoint holds auth alone.
            // OTelReceiverBody models both editions, so the checked body is
            // asserted onto the ultimate-only generated type here.
            body: buildReceiverBody(
              input
            ) as components['schemas']['OTelCollectorReceiverRequestSpec']
          })
        )
        return {
          ok: true,
          rollback: async () => {
            // The receiver DELETE endpoint enforces ETag locking — see IF_MATCH_ANY.
            await client.DELETE('/objects/otel_collector_config_receivers/{config_id}', {
              params: { header: IF_MATCH_ANY, path: { config_id: input.id } }
            })
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
        // Typed as required because the schema gives them a default; both mirror
        // the server-side default of null.
        comment: null,
        docu_url: null,
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
        unwrap(
          await client.POST('/domain-types/otel_collector_config_prom_scrape/collections/all', {
            params: { header: CONTENT_TYPE_JSON },
            body
          })
        )
        return {
          ok: true,
          rollback: async () => {
            // The prom-scrape DELETE endpoint enforces ETag locking — see IF_MATCH_ANY.
            await client.DELETE('/objects/otel_collector_config_prom_scrape/{config_id}', {
              params: { header: IF_MATCH_ANY, path: { config_id: input.id } }
            })
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
        const body = unwrap(
          await client.POST('/domain-types/otel_collector_config_bundles/collections/all', {
            params: { header: CONTENT_TYPE_JSON },
            body: {
              title: input.configName,
              // Typed as required because the schema gives it a default; mirrors
              // the server-side default of null.
              comment: null,
              site: input.siteId,
              otel_config_id: input.configName,
              dcd_connection_id: `quick_setup_${input.configName}`,
              password_ids: input.passwordIds
            }
          })
        )
        const bundleId = body.extensions.bundle_id
        if (!bundleId) {
          return { ok: true }
        }
        return {
          ok: true,
          rollback: async () => {
            await client.DELETE('/objects/otel_collector_config_bundles/{bundle_id}', {
              params: { path: { bundle_id: bundleId } }
            })
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
  enableDataBackendAction,
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
    enableDataBackendAction,
    createPrometheusScrapeConfigAction(input),
    createDCDConnectorAction,
    createOTelBundleAction({ configName: input.id, siteId: input.siteId, passwordIds: [] })
  ]
}
