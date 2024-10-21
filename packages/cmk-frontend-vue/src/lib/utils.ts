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
