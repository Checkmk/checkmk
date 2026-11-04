/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { randomId } from 'cmk-ui-library/lib/randomId'

const KEY = 'cmk-maps-stream-tabs'

export interface StreamTab {
  readonly name: string
  /** For a page whose name another took: a duplicated tab copies the storage. */
  rename(): void
}

/**
 * The name this page gives its browser tab in the stream URL, kept over a reload.
 *
 * The daemon notices a closed stream only when it next writes to it, so a reloaded
 * page has to take over the slot of the stream it replaces. The page takes a name
 * out of the tab's storage while it is shown and puts it back when it goes, so the
 * frames of a reloaded tab each find one.
 */
export function claimStreamTab(): StreamTab {
  let tab = take() ?? randomId()
  window.addEventListener('pagehide', () => put(tab))
  window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
      remove(tab)
    }
  })
  return {
    get name() {
      return tab
    },
    rename() {
      tab = randomId()
    }
  }
}

function names(): string[] {
  const stored: unknown = JSON.parse(sessionStorage.getItem(KEY) ?? '[]')
  return Array.isArray(stored)
    ? stored.filter((name): name is string => typeof name === 'string')
    : []
}

function take(): string | null {
  try {
    const [tab, ...rest] = names()
    sessionStorage.setItem(KEY, JSON.stringify(rest))
    return tab ?? null
  } catch {
    return null
  }
}

function store(change: (tabs: string[]) => string[]): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(change(names())))
  } catch {
    // Without storage a reload names a new tab.
  }
}

function put(tab: string): void {
  store((tabs) => [...tabs.filter((name) => name !== tab), tab])
}

function remove(tab: string): void {
  store((tabs) => tabs.filter((name) => name !== tab))
}
