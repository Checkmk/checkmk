/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export const storageHandler = {
  get: (storage: Storage, key: string, defaultValue: unknown = null): unknown => {
    const value = storage.getItem(key)
    if (value) {
      return JSON.parse(value)
    }
    return defaultValue
  },

  set: (storage: Storage, key: string, value: unknown): void => {
    storage.setItem(key, JSON.stringify(value))
  }
}

export function capitalizeFirstLetter(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

export const wait = async (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms))
