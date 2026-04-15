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
 * Ordered list of steps run by the QuickSetup finalize stage. To add a new
 * verify-and-add-change step append a new `PostSaveAction` here.
 */
export const POST_SAVE_ACTIONS: readonly PostSaveAction[] = [enableCollectorAction]
