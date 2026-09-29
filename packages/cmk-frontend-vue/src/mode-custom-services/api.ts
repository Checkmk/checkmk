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
  CustomServiceUpdate
} from './definition'

export interface SaveResult {
  ok: boolean
  error?: string
}

export type LoadResult =
  | { ok: true; extensions: CustomServiceExtensions; etag: string }
  | { ok: false; error: string }

function isClientError(error: unknown): error is CmkApiError {
  return error instanceof CmkApiError && error.statusCode < 500
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
      return { ok: false, error: error.message }
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
      return { ok: false, error: error.message }
    }
    throw error
  }
}
