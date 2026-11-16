/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { type Ref, computed } from 'vue'

import { type ResolveResult, resolveHostNameTemplate } from './api'
import { type Lookup, useDebouncedLookup } from './debouncedLookup'
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
        (resolution.matching_hosts.length === 0 && resolution.unmatched_host_names.length === 0) ||
        resolution.hidden_match_count > 0 ||
        resolution.truncated
      )
    }
    default:
      return false
  }
}

/** Whether saving creates hosts, as far as the preview knows. */
export function templatePreviewCreatesHosts(preview: TemplatePreview): boolean {
  return preview.status === 'resolved' && preview.resolution.unmatched_host_names.length > 0
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

function previewOf(lookup: Lookup<ResolveResult>): TemplatePreview {
  switch (lookup.status) {
    case 'idle':
    case 'loading':
      return lookup
    case 'done':
      return lookup.result.ok
        ? { status: 'resolved', resolution: lookup.result.resolution }
        : { status: 'refused', error: lookup.result.refusal }
    case 'failed':
      return {
        status: 'failed',
        error: lookup.timedOut
          ? _t('Looking up the matching hosts took too long.')
          : lookup.error instanceof Error
            ? lookup.error.message
            : _t('The matching hosts could not be looked up.')
      }
  }
}

/**
 * Resolves the host name template of the model to the hosts it matches. Edits are debounced. A
 * null model resolves nothing.
 */
export function useHostNameTemplatePreview(
  getModel: () => ServiceModel | null,
  { debounceMs = DEFAULT_DEBOUNCE_MS, timeoutMs = DEFAULT_TIMEOUT_MS } = {}
): HostNameTemplatePreview {
  const lookup = useDebouncedLookup(() => requestOf(getModel()), resolveHostNameTemplate, {
    debounceMs,
    timeoutMs
  })
  return { preview: computed(() => previewOf(lookup.value)) }
}
