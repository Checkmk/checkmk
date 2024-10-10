/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getIconVariable(iconName: string | undefined): string {
  /*
     Transform from icon file name pattern
        "icon_<underscored_name>.<file_extension>" or "<underscored_name>.<file_extension>"
     to CSS variable name pattern, returned as a call to the CSS fct var()
        "var(--icon-<dashed_name>)"

     E.g. "icon_main_help.svg" -> "var(--icon-main-help)"
  */
  if (!iconName) {
    return 'none'
  }

  let iconVar: string = `${iconName.startsWith('icon') ? iconName : ['icon', iconName].join('-')}`
  iconVar = iconVar.replace(/_/g, '-').split('.')[0]!
  return `var(--${iconVar})`
}

export const localStorageHandler = {
  get: (key: string, defaultValue: unknown = null): unknown => {
    const value = localStorage.getItem(key)
    if (value) {
      return JSON.parse(value)
    }
    return defaultValue
  },

  set: (key: string, value: unknown): void => {
    localStorage.setItem(key, JSON.stringify(value))
  }
}
