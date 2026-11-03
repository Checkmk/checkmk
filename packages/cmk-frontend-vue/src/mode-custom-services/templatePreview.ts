/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { type Ref, onScopeDispose, ref, watch } from 'vue'

import { resolveHostNameTemplate } from './api'
import type { HostNameTemplateResolution, HostNameTemplateResolutionRequest } from './definition'
import type { ServiceModel } from './types'

const { _t } = usei18n()

const DEFAULT_DEBOUNCE_MS = 500
const DEFAULT_TIMEOUT_MS = 30_000

export type TemplatePreview =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'resolved'; resolution: HostNameTemplateResolution }
  | { status: 'refused'; error: string }
  | { status: 'failed'; error: string }

export interface HostNameTemplatePreview {
  preview: Readonly<Ref<TemplatePreview>>
  refresh: () => void
}

/**
 * Blocks what saving is known to refuse. A failed lookup does not block: saving resolves the
 * template again and states its own refusal.
 */
export function templatePreviewBlocksSave(preview: TemplatePreview): boolean {
  switch (preview.status) {
    case 'loading':
    case 'refused':
      return true
    case 'resolved': {
      const { resolution } = preview
      return (
        resolution.matching_hosts.length === 0 ||
        resolution.hidden_match_count > 0 ||
        resolution.truncated
      )
    }
    default:
      return false
  }
}

function requestOf(model: ServiceModel | null): HostNameTemplateResolutionRequest | null {
  if (model === null) {
    return null
  }
  const { metricName, attributeFilter, consolidation, aggregator, hostNameTemplate } = model
  if (metricName === null || hostNameTemplate === null || hostNameTemplate.trim() === '') {
    return null
  }
  return {
    metric_name: metricName,
    host_name_template: hostNameTemplate,
    ...(attributeFilter === undefined ? {} : { attribute_filter: attributeFilter }),
    consolidation,
    ...(aggregator === undefined ? {} : { aggregator })
  }
}

function withSortedKeys(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(withSortedKeys)
  }
  if (typeof value === 'object' && value !== null) {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
        .map(([key, entry]) => [key, withSortedKeys(entry)])
    )
  }
  return value
}

/**
 * Resolves the host name template of the model to the hosts it matches. Edits are debounced,
 * `refresh` asks at once. A null model resolves nothing.
 */
export function useHostNameTemplatePreview(
  getModel: () => ServiceModel | null,
  { debounceMs = DEFAULT_DEBOUNCE_MS, timeoutMs = DEFAULT_TIMEOUT_MS } = {}
): HostNameTemplatePreview {
  const preview = ref<TemplatePreview>({ status: 'idle' })
  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  let inFlight: AbortController | null = null

  function cancel(): void {
    if (debounceTimer !== null) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
    inFlight?.abort()
    inFlight = null
  }

  async function load(body: HostNameTemplateResolutionRequest): Promise<void> {
    const controller = new AbortController()
    inFlight = controller
    let timedOut = false
    const timeout = setTimeout(() => {
      timedOut = true
      controller.abort()
    }, timeoutMs)
    try {
      const result = await resolveHostNameTemplate(body, controller.signal)
      if (inFlight === controller) {
        preview.value = result.ok
          ? { status: 'resolved', resolution: result.resolution }
          : { status: 'refused', error: result.refusal }
      }
    } catch (error) {
      if (inFlight !== controller) {
        return
      }
      preview.value = {
        status: 'failed',
        error: timedOut
          ? _t('Looking up the matching hosts took too long.')
          : error instanceof Error
            ? error.message
            : _t('The matching hosts could not be looked up.')
      }
    } finally {
      clearTimeout(timeout)
      if (inFlight === controller) {
        inFlight = null
      }
    }
  }

  function schedule(): void {
    cancel()
    const body = requestOf(getModel())
    if (body === null) {
      preview.value = { status: 'idle' }
      return
    }
    // Shown at once, so no list of an earlier template is left standing during the debounce
    preview.value = { status: 'loading' }
    debounceTimer = setTimeout(() => {
      debounceTimer = null
      void load(body)
    }, debounceMs)
  }

  function refresh(): void {
    const body = requestOf(getModel())
    if (body === null) {
      return
    }
    cancel()
    preview.value = { status: 'loading' }
    void load(body)
  }

  // A serialized key with sorted keys, so an equal request in a new object or another key order
  // does not ask again
  watch(() => JSON.stringify(withSortedKeys(requestOf(getModel()))), schedule, {
    immediate: true
  })
  onScopeDispose(cancel)

  return { preview, refresh }
}
