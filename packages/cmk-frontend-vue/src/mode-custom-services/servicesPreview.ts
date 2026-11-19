/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import usei18n from 'cmk-ui-library/lib/i18n'
import { type Ref, computed, shallowRef, watch } from 'vue'

import { resolveServices } from './api'
import { type Lookup, requestKey, useDebouncedLookup } from './debouncedLookup'
import {
  type CompleteModel,
  type ServicesToCreate,
  type ServicesToCreateRequest,
  aggregationProblem,
  buildResolveServicesRequest
} from './definition'
import type { ServiceModel } from './types'

const { _t } = usei18n()

const DEFAULT_DEBOUNCE_MS = 500
const DEFAULT_TIMEOUT_MS = 30_000

/**
 * The services saving creates. A refusal is a 400 on a host name template, e.g. one the grouping
 * does not allow: the template preview already explains it. While a lookup that only changed the
 * folders of new hosts is pending, the services found before stay shown as refreshing. A refused
 * change of folders fails instead, as the template preview does not explain it.
 */
export type ServicesPreview =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'resolved'; services: ServicesToCreate }
  | { status: 'refreshing'; services: ServicesToCreate }
  | { status: 'refused' }
  | { status: 'failed'; error: string }

export interface ServicesPreviewLookup {
  preview: Readonly<Ref<ServicesPreview>>
}

/**
 * Blocks what saving is known to refuse: names that clash, also while only the folders of new hosts
 * are looked up again. A pending or failed lookup does not block: saving resolves the names again
 * and states its own refusal.
 */
export function servicesPreviewBlocksSave(preview: ServicesPreview): boolean {
  return (
    (preview.status === 'resolved' || preview.status === 'refreshing') &&
    preview.services.clashes.length > 0
  )
}

function completeModel(model: ServiceModel): CompleteModel | null {
  const { metricName, hostName, hostNameTemplate, serviceName, consolidation } = model
  if (
    metricName === null ||
    serviceName.trim() === '' ||
    aggregationProblem(consolidation) !== undefined
  ) {
    return null
  }
  if (hostNameTemplate !== null) {
    return hostNameTemplate.trim() === ''
      ? null
      : { ...model, metricName, hostName: null, hostNameTemplate }
  }
  return hostName === null || hostName.trim() === ''
    ? null
    : { ...model, metricName, hostName, hostNameTemplate }
}

function requestOf(
  model: ServiceModel | null,
  configurationName: string | null,
  newHostFolders: Record<string, string>
): ServicesToCreateRequest | null {
  const complete = model === null ? null : completeModel(model)
  return complete === null
    ? null
    : buildResolveServicesRequest(complete, configurationName, newHostFolders)
}

interface ResolvedServices {
  /** The request without the folders of new hosts, which do not change the services */
  key: string
  services: ServicesToCreate
}

function keyWithoutFolders(request: ServicesToCreateRequest): string {
  return requestKey({ ...request, new_host_folders: undefined })
}

function previewOf(
  lookup: Lookup<ResolvedServices>,
  explainedByTemplatePreview: boolean,
  requested: string | null,
  shown: ResolvedServices | null
): ServicesPreview {
  switch (lookup.status) {
    case 'idle':
      return lookup
    case 'loading':
      return shown !== null && shown.key === requested
        ? { status: 'refreshing', services: shown.services }
        : lookup
    case 'done':
      return { status: 'resolved', services: lookup.result.services }
    case 'failed':
      if (
        explainedByTemplatePreview &&
        shown?.key !== requested &&
        lookup.error instanceof CmkApiError &&
        lookup.error.statusCode === 400
      ) {
        return { status: 'refused' }
      }
      return {
        status: 'failed',
        error: lookup.timedOut
          ? _t('Looking up the services to be created took too long.')
          : lookup.error instanceof Error
            ? lookup.error.message
            : _t('The services to be created could not be looked up.')
      }
  }
}

/**
 * Resolves the services the model creates, with their names and hosts. Edits are debounced. A null
 * model resolves nothing. ``configurationName`` is the stored custom service being edited, whose
 * own services are no clash. ``getNewHostFolders`` names the folders of the hosts saving creates,
 * which are checked as when saving.
 */
export function useServicesPreview(
  getModel: () => ServiceModel | null,
  configurationName: string | null = null,
  {
    debounceMs = DEFAULT_DEBOUNCE_MS,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    getNewHostFolders = (): Record<string, string> => ({})
  } = {}
): ServicesPreviewLookup {
  const getRequest = () => requestOf(getModel(), configurationName, getNewHostFolders())
  const lookup = useDebouncedLookup(
    getRequest,
    async (request: ServicesToCreateRequest, signal: AbortSignal): Promise<ResolvedServices> => ({
      key: keyWithoutFolders(request),
      services: await resolveServices(request, signal)
    }),
    { debounceMs, timeoutMs }
  )
  const shown = shallowRef<ResolvedServices | null>(null)
  watch(
    lookup,
    (current) => {
      if (current.status === 'done') {
        shown.value = current.result
      } else if (current.status === 'idle') {
        shown.value = null
      }
    },
    { flush: 'sync' }
  )
  return {
    preview: computed(() => {
      const request = getRequest()
      return previewOf(
        lookup.value,
        (getModel()?.hostNameTemplate ?? null) !== null,
        request === null ? null : keyWithoutFolders(request),
        shown.value
      )
    })
  }
}
