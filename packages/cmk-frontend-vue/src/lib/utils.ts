/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from '@/lib/i18n'

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
  // Check if clipboard API is available
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return
    } catch {
      // continue to fallback method
    }
  }
  fallbackCopyToClipboard(text)
}

function fallbackCopyToClipboard(text: string) {
  const { _t } = usei18n()

  // Use a contenteditable div which has better focus support
  const container = document.createElement('div')
  container.contentEditable = 'true'
  container.style.position = 'absolute'
  container.style.left = '-9999px'
  container.style.top = '-9999px'
  container.style.whiteSpace = 'pre'
  container.textContent = text

  document.body.appendChild(container)
  container.focus()

  // Select all text in the container using Range API
  const range = document.createRange()
  range.selectNodeContents(container)
  const selection = window.getSelection()

  if (selection) {
    selection.removeAllRanges()
    selection.addRange(range)
    const selectedText = selection.toString()
    try {
      const result = document.execCommand('copy')
      selection.removeAllRanges()
      document.body.removeChild(container)
      if (!result) {
        console.error('[fallbackCopyToClipboard] execCommand returned false:')
        throw new Error(_t('Copy failed: this might be due to browser security restrictions.'))
      }
      // Additional check: if nothing was selected, the copy _likely_ failed
      if (!selectedText || selectedText.length === 0) {
        throw new Error(_t('Copy failed: no text was selected.'))
      }
    } catch (error) {
      selection.removeAllRanges()
      if (document.body.contains(container)) {
        document.body.removeChild(container)
      }
      console.error('[fallbackCopyToClipboard] Catch block error:', error)
      throw error instanceof Error ? error : new Error(_t('Failed to copy to clipboard'))
    }
  } else {
    document.body.removeChild(container)
    console.error('[fallbackCopyToClipboard] No selection object available.')
    throw new Error(_t('Copy failed.'))
  }
}
