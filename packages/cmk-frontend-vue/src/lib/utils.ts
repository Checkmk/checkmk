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

export async function copyToClipboard(text: string): Promise<void> {
  try {
    // Check if clipboard API is available
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      fallbackCopyToClipboard(text)
    }
  } catch (err) {
    console.error('Failed to copy to clipboard:', err)
    throw err
  }
}

function fallbackCopyToClipboard(text: string) {
  const textArea = document.createElement('textarea')
  textArea.value = text

  // Avoid scrolling to bottom
  textArea.style.top = '0'
  textArea.style.left = '0'
  textArea.style.position = 'fixed'

  document.body.appendChild(textArea)
  textArea.focus()
  textArea.select()

  try {
    const result = document.execCommand('copy')
    if (!result) {
      throw new Error('Fallback copy to clipboard command was unsuccessful')
    }
  } finally {
    document.body.removeChild(textArea)
  }
}
