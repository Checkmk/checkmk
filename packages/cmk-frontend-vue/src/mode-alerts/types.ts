/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export type ServiceNameMatch = 'exact' | 'regex'

export interface AlertModel {
  name: string
  matchType: ServiceNameMatch
  servicePattern: string
}

export function emptyAlert(): AlertModel {
  return { name: '', matchType: 'exact', servicePattern: '' }
}

export function alertName(model: AlertModel): string {
  return model.name.trim()
}

export function servicePattern(model: AlertModel): string {
  return model.servicePattern.trim()
}

// The Livestatus and JavaScript dialects differ, so this only rules out patterns broken
// in both; Livestatus rejects the rest with a 400.
export function hasUnparsableRegex(model: AlertModel): boolean {
  const pattern = servicePattern(model)
  if (model.matchType !== 'regex' || pattern === '') {
    return false
  }
  try {
    new RegExp(pattern)
    return false
  } catch {
    return true
  }
}
