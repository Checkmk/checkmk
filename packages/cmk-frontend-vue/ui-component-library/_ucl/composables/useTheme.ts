/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { readonly, ref } from 'vue'

export type Theme = 'facelift' | 'modern-dark'

const QUERY_THEMES: Record<string, Theme> = {
  light: 'facelift',
  dark: 'modern-dark'
}

function readQueryTheme(): Theme | undefined {
  const value = new URLSearchParams(window.location.search).get('theme')
  return value !== null && Object.hasOwn(QUERY_THEMES, value) ? QUERY_THEMES[value] : undefined
}

const STORAGE_KEY = 'ucl-theme'

function isTheme(value: unknown): value is Theme {
  return value === 'facelift' || value === 'modern-dark'
}

function readStoredTheme(): Theme | undefined {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return isTheme(stored) ? stored : undefined
  } catch {
    return undefined
  }
}

function storeTheme(theme: Theme) {
  try {
    localStorage.setItem(STORAGE_KEY, theme)
  } catch {
    return
  }
}

function removeQueryTheme() {
  const url = new URL(window.location.href)
  if (url.searchParams.has('theme')) {
    url.searchParams.delete('theme')
    window.history.replaceState(window.history.state, '', url)
  }
}

const currentTheme = ref<Theme>('facelift')

function applyTheme(theme: Theme) {
  currentTheme.value = theme
  document.body.dataset['theme'] = theme
}

function setTheme(theme: Theme) {
  applyTheme(theme)
  storeTheme(theme)
  removeQueryTheme()
}

applyTheme(readQueryTheme() ?? readStoredTheme() ?? 'facelift')

function getByTheme<T>(faceliftValue: T, modernDarkValue: T): T {
  return currentTheme.value === 'modern-dark' ? modernDarkValue : faceliftValue
}

export function useTheme() {
  return {
    currentTheme: readonly(currentTheme),
    setTheme,
    getByTheme
  }
}
