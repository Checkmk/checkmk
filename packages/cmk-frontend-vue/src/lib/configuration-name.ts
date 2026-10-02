/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

const NAME_PATTERN = /^[a-zA-Z_][a-zA-Z0-9_-]*$/

export function nextAvailableConfigName(existingIds: string[], prefix: string): string {
  const escapedPrefix = prefix.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const pattern = new RegExp(`^${escapedPrefix}(\\d+)$`)
  let max = 0
  for (const id of existingIds) {
    const match = pattern.exec(id)
    if (match) {
      max = Math.max(max, Number(match[1]))
    }
  }
  return `${prefix}${max + 1}`
}

export function configNameFormatErrors(name: string): string[] {
  if (!name.trim()) {
    return [_t('Configuration name is required but not specified.')]
  }
  if (!NAME_PATTERN.test(name)) {
    return [
      _t(
        'The name must only consist of letters, digits, dash and underscore and it must start with a letter or underscore.'
      )
    ]
  }
  return []
}

export function configNameTakenErrors(name: string, existingIds: string[]): string[] {
  if (existingIds.includes(name)) {
    return [_t('A configuration with this name already exists. Choose a different name.')]
  }
  return []
}
