/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TwoColumnDictionary } from 'cmk-shared-typing/typescript/vue_formspec_components'

import type { OAuth2FormData } from '@/mode-oauth2-connection/lib/service/oauth2-connection-api.ts'

/** UUID v4 regex pattern */
export const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export function isValidUUID(value: string): boolean {
  return UUID_REGEX.test(value)
}

export function buildRedirectUri(redirectUrl: string): string {
  const baseUri = (
    location.origin +
    location.pathname.replace('wato.py', '') +
    redirectUrl
  ).replace('index.py', 'wato.py')

  const url = new URL(baseUri)
  url.searchParams.delete('connector_type')
  url.searchParams.delete('clone')
  url.searchParams.delete('ident')
  url.searchParams.delete('entity_type_specifier')
  return url.toString()
}

export function filteredDataInFilteredDictionary(
  data: OAuth2FormData,
  filteredDictionary: TwoColumnDictionary
): Partial<OAuth2FormData> {
  const filteredData = { ...data }
  const dictionaryKeys = new Set(filteredDictionary.elements.map((e) => e.name))

  for (const key of Object.keys(data) as Array<keyof OAuth2FormData>) {
    if (!dictionaryKeys.has(key)) {
      delete filteredData[key]
    }
  }

  return filteredData
}

export function filteredDictionaryByGroupName(
  dictionary: TwoColumnDictionary,
  groupName: string
): TwoColumnDictionary {
  return {
    ...dictionary,
    elements: dictionary.elements.filter((element) => element.group?.title === groupName)
  }
}
