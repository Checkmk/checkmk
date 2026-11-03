/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  DataBackendSettings,
  Dictionary
} from 'cmk-shared-typing/typescript/vue_formspec_components'

export const ADDRESS_SEEN_BY_CENTRAL = 'address_seen_by_central'

export function centrallyRoutedFeatures(
  spec: DataBackendSettings,
  data: Record<string, unknown>
): string[] {
  const locations = (data['features'] ?? {}) as Record<string, unknown>
  return Object.keys(locations).filter((feature) => locations[feature] === spec.central_location)
}

export function placesAFeatureCentrally(
  spec: DataBackendSettings,
  data: Record<string, unknown>
): boolean {
  return centrallyRoutedFeatures(spec, data).length > 0
}

export function dictionaryOf(
  spec: DataBackendSettings,
  includes: (name: string) => boolean
): Dictionary {
  const { central_location: _centralLocation, ...dictionary } = spec
  return {
    ...dictionary,
    type: 'dictionary',
    elements: spec.elements.filter((element) => includes(element.name))
  }
}
