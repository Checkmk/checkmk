/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError, CmkSimpleError } from 'cmk-ui-library/lib/error'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type {
  CustomServiceDefinition,
  CustomServiceExtensions,
  CustomServiceUpdate,
  HostNameTemplateResolution,
  HostNameTemplateResolutionRequest,
  TemplateAttributes,
  TemplateAttributesRequest
} from './definition'

/**
 * A refusal is the server's verdict on the template, always a 400: saving the same template would
 * be refused too. Any other error says nothing about the template.
 */
export type ResolveResult =
  | { ok: true; resolution: HostNameTemplateResolution }
  | { ok: false; refusal: string }

export interface SaveResult {
  ok: boolean
  error?: string
  /** Why the endpoint refused the host name template, to be shown at the template field. */
  templateError?: string
}

export type LoadResult =
  | { ok: true; extensions: CustomServiceExtensions; etag: string }
  | { ok: false; error: string }

function isClientError(error: unknown): error is CmkApiError {
  return error instanceof CmkApiError && error.statusCode < 500
}

// Only a template that is the sole problem is shown at its field, so no other problem goes unseen
function templateErrorOf(body: unknown): string | undefined {
  const fields = (body as { fields?: unknown } | null | undefined)?.fields
  if (typeof fields !== 'object' || fields === null) {
    return undefined
  }
  const [field, ...others] = Object.values(fields)
  if (field === undefined || others.length > 0) {
    return undefined
  }
  const { loc, msg } = field as { loc?: unknown; msg?: unknown }
  return Array.isArray(loc) && loc.at(-1) === 'host_name_template' && typeof msg === 'string'
    ? msg.replace(/^Value error,\s*/, '')
    : undefined
}

function refusal(error: CmkApiError): SaveResult {
  const templateError = templateErrorOf(error.body)
  return templateError === undefined
    ? { ok: false, error: error.message }
    : { ok: false, error: error.message, templateError }
}

export async function saveCustomServiceDefinition(
  definition: CustomServiceDefinition
): Promise<SaveResult> {
  try {
    unwrap(
      await client.POST('/domain-types/custom_service/collections/all', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: definition
      })
    )
    return { ok: true }
  } catch (error) {
    if (isClientError(error)) {
      return refusal(error)
    }
    throw error
  }
}

export async function loadCustomServiceDefinition(configurationName: string): Promise<LoadResult> {
  try {
    const result = await client.GET('/objects/custom_service/{configuration_name}', {
      params: { path: { configuration_name: configurationName } }
    })
    const service = unwrap(result)
    const etag = result.response.headers.get('ETag')
    // The endpoint always sends one; without it a later update could not detect a concurrent
    // change.
    if (etag === null) {
      throw new CmkSimpleError(
        'The server answered without a version identifier for this custom service. Reload the page to load it again.'
      )
    }
    return { ok: true, extensions: service.extensions, etag }
  } catch (error) {
    if (isClientError(error)) {
      return { ok: false, error: error.message }
    }
    throw error
  }
}

export async function updateCustomServiceDefinition(
  configurationName: string,
  update: CustomServiceUpdate,
  etag: string
): Promise<SaveResult> {
  try {
    unwrap(
      await client.PUT('/objects/custom_service/{configuration_name}', {
        params: {
          path: { configuration_name: configurationName },
          header: { 'Content-Type': 'application/json', 'If-Match': etag }
        },
        body: update
      })
    )
    return { ok: true }
  } catch (error) {
    if (isClientError(error)) {
      return refusal(error)
    }
    throw error
  }
}

export async function listCustomServiceNames(): Promise<string[]> {
  return unwrap(await client.GET('/domain-types/custom_service/collections/all'))
    .value.map((service) => service.id)
    .filter((id): id is string => typeof id === 'string')
}

export async function fetchTemplateAttributes(
  request: TemplateAttributesRequest
): Promise<TemplateAttributes> {
  return unwrap(
    await client.POST('/domain-types/custom_service/actions/template_attributes/invoke', {
      params: { header: { 'Content-Type': 'application/json' } },
      body: request
    })
  )
}

export async function resolveHostNameTemplate(
  request: HostNameTemplateResolutionRequest,
  signal: AbortSignal
): Promise<ResolveResult> {
  try {
    const resolution = unwrap(
      await client.POST('/domain-types/custom_service/actions/resolve_host_name_template/invoke', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: request,
        signal
      })
    )
    return { ok: true, resolution }
  } catch (error) {
    if (error instanceof CmkApiError && error.statusCode === 400) {
      return { ok: false, refusal: templateErrorOf(error.body) ?? error.message }
    }
    throw error
  }
}
