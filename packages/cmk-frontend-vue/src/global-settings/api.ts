/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  GlobalSettingsApp,
  GlobalSettingsOrigin,
  GlobalSettingsVariable
} from 'cmk-shared-typing/typescript/global_settings'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import { CmkSimpleError } from 'cmk-ui-library/lib/error'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'
import type { InjectionKey } from 'vue'

import type { ValidationMessages } from '@/form'

export type GlobalSettingsScope = GlobalSettingsApp['scope']

export type ToggleSetting = (
  variable: GlobalSettingsVariable,
  value: boolean
) => Promise<TranslatedString | null>

export const GLOBAL_SETTINGS_TOGGLE: InjectionKey<ToggleSetting> = Symbol('GlobalSettingsToggle')

export interface ReceivedValue {
  value: unknown
  spec: GlobalSettingsVariable['spec']
  origin: GlobalSettingsOrigin
  etag: string
}

export type SaveResult =
  | { type: 'saved'; received: ReceivedValue }
  | { type: 'invalid'; validationMessages: ValidationMessages }

export interface GlobalSettingsService {
  load(varname: string): Promise<ReceivedValue>
  save(varname: string, value: unknown, etag: string): Promise<SaveResult>
  reset(varname: string, etag: string): Promise<void>
}

const CONTENT_TYPE_HEADER = { 'Content-Type': 'application/json' } as const

interface SettingResult {
  data?: { value: unknown; spec: unknown; origin: GlobalSettingsOrigin }
  error?: unknown
  response: Response
}

function toReceivedValue(result: SettingResult): ReceivedValue {
  const body = unwrap(result)
  const etag = result.response.headers.get('ETag')
  if (etag === null) {
    throw new CmkSimpleError(
      'The server answered without a version identifier for this setting. Reload the page to see its current state.'
    )
  }
  return {
    value: body.value,
    // The REST API declares the form spec as an untyped object.
    spec: body.spec as GlobalSettingsVariable['spec'],
    origin: body.origin,
    etag
  }
}

function isValidationRejection(
  result: SettingResult
): result is SettingResult & { error: components['schemas']['GlobalSettingValidation422'] } {
  const error = result.error as { ext?: { validation_errors?: unknown } } | null | undefined
  return result.response.status === 422 && error?.ext?.validation_errors !== undefined
}

function toSaveResult(result: SettingResult): SaveResult {
  if (isValidationRejection(result)) {
    // The predicate's GlobalSettingValidation422 makes sure that the frontend model
    // (ValidationMessages) is in sync with the documented error response. Do not simplify this!
    return { type: 'invalid', validationMessages: result.error.ext.validation_errors }
  }
  return { type: 'saved', received: toReceivedValue(result) }
}

function globalScopeService(): GlobalSettingsService {
  return {
    async load(varname) {
      return toReceivedValue(
        await client.GET('/objects/global_setting/{varname}', {
          params: { path: { varname } }
        })
      )
    },

    async save(varname, value, etag) {
      return toSaveResult(
        await client.PUT('/objects/global_setting/{varname}', {
          params: { path: { varname }, header: { ...CONTENT_TYPE_HEADER, 'If-Match': etag } },
          body: { value }
        })
      )
    },

    async reset(varname, etag) {
      unwrap(
        await client.DELETE('/objects/global_setting/{varname}', {
          params: { path: { varname }, header: { 'If-Match': etag } }
        })
      )
    }
  }
}

function siteScopeService(siteId: string): GlobalSettingsService {
  return {
    async load(varname) {
      return toReceivedValue(
        await client.GET('/objects/site_connection/{site_id}/global_setting/{varname}', {
          params: { path: { site_id: siteId, varname } }
        })
      )
    },

    async save(varname, value, etag) {
      return toSaveResult(
        await client.PUT('/objects/site_connection/{site_id}/global_setting/{varname}', {
          params: {
            path: { site_id: siteId, varname },
            header: { ...CONTENT_TYPE_HEADER, 'If-Match': etag }
          },
          body: { value }
        })
      )
    },

    async reset(varname, etag) {
      unwrap(
        await client.DELETE('/objects/site_connection/{site_id}/global_setting/{varname}', {
          params: { path: { site_id: siteId, varname }, header: { 'If-Match': etag } }
        })
      )
    }
  }
}

export function createGlobalSettingsService(scope: GlobalSettingsScope): GlobalSettingsService {
  switch (scope.type) {
    case 'global':
      return globalScopeService()
    case 'site':
      return siteScopeService(scope.site_id)
  }
}
