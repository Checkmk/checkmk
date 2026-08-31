/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  GlobalSettingsApp,
  GlobalSettingsVariable
} from 'cmk-shared-typing/typescript/global_settings'
import { CmkSimpleError } from 'cmk-ui-library/lib/error'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'
import type { InjectionKey } from 'vue'

export type GlobalSettingsScope = GlobalSettingsApp['scope']

export type ToggleSetting = (
  variable: GlobalSettingsVariable,
  value: boolean
) => Promise<TranslatedString | null>

export const GLOBAL_SETTINGS_TOGGLE: InjectionKey<ToggleSetting> = Symbol('GlobalSettingsToggle')

export interface ReceivedValue {
  value: unknown
  isDefault: boolean
  etag: string
}

export interface GlobalSettingsService {
  load(scope: GlobalSettingsScope, varname: string): Promise<ReceivedValue>
  save(
    scope: GlobalSettingsScope,
    varname: string,
    value: unknown,
    etag: string
  ): Promise<ReceivedValue>
  reset(scope: GlobalSettingsScope, varname: string, etag: string): Promise<void>
}

export const GLOBAL_SETTINGS_SERVICE: InjectionKey<GlobalSettingsService> =
  Symbol('GlobalSettingsService')

const CONTENT_TYPE_HEADER = { 'Content-Type': 'application/json' } as const

function toReceivedValue(result: {
  data?: { value: unknown; is_default: boolean }
  response: Response
}): ReceivedValue {
  const body = unwrap(result)
  const etag = result.response.headers.get('ETag')
  if (etag === null) {
    throw new CmkSimpleError(
      'The server answered without a version identifier for this setting. Reload the page to see its current state.'
    )
  }
  return { value: body.value, isDefault: body.is_default, etag }
}

export const globalSettingsService: GlobalSettingsService = {
  async load(scope, varname) {
    if (scope.type === 'site') {
      return toReceivedValue(
        await client.GET('/objects/site_connection/{site_id}/global_setting/{varname}', {
          params: { path: { site_id: scope.site_id, varname } }
        })
      )
    }
    return toReceivedValue(
      await client.GET('/objects/global_setting/{varname}', { params: { path: { varname } } })
    )
  },

  async save(scope, varname, value, etag) {
    const header = { ...CONTENT_TYPE_HEADER, 'If-Match': etag }
    if (scope.type === 'site') {
      return toReceivedValue(
        await client.PUT('/objects/site_connection/{site_id}/global_setting/{varname}', {
          params: { path: { site_id: scope.site_id, varname }, header },
          body: { value }
        })
      )
    }
    return toReceivedValue(
      await client.PUT('/objects/global_setting/{varname}', {
        params: { path: { varname }, header },
        body: { value }
      })
    )
  },

  async reset(scope, varname, etag) {
    const header = { 'If-Match': etag }
    if (scope.type === 'site') {
      unwrap(
        await client.DELETE('/objects/site_connection/{site_id}/global_setting/{varname}', {
          params: { path: { site_id: scope.site_id, varname }, header }
        })
      )
      return
    }
    unwrap(
      await client.DELETE('/objects/global_setting/{varname}', {
        params: { path: { varname }, header }
      })
    )
  }
}
