/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { reactive } from 'vue'

/**
 * Connections, map/object defaults and logging/integration settings all live in
 * Checkmk's native global settings (Customize → Maps → the "Maps" page menu) —
 * not in an in-SPA admin tab. Only the image library remains maps-own.
 */
export type AdminTab = 'icons'

export type NavTarget =
  | { view: 'home' }
  | { view: 'map'; name: string; kiosk?: boolean; preview?: boolean }
  | { view: 'admin'; tab: AdminTab }

export interface NavState {
  view: 'home' | 'map' | 'admin'
  name: string | null
  tab: AdminTab | null
  kiosk: boolean
  preview: boolean
}

const ADMIN_TABS: readonly AdminTab[] = ['icons']

function isAdminTab(value: string | null): value is AdminTab {
  return value !== null && (ADMIN_TABS as readonly string[]).includes(value)
}

function parse(search: string): NavState {
  const params = new URLSearchParams(search)
  const mode = params.get('mode')
  const name = params.get('name')
  const kiosk = params.get('kiosk') === '1'
  const preview = params.get('preview') === '1'
  if (isAdminTab(mode)) {
    return { view: 'admin', name: null, tab: mode, kiosk: false, preview: false }
  }
  if (name) {
    return { view: 'map', name, tab: null, kiosk, preview }
  }
  return { view: 'home', name: null, tab: null, kiosk: false, preview: false }
}

function buildUrl(target: NavTarget): string {
  const path = window.location.pathname
  const params = new URLSearchParams()
  if (target.view === 'map') {
    params.set('name', target.name)
    if (target.kiosk) {
      params.set('kiosk', '1')
    }
    if (target.preview) {
      params.set('preview', '1')
    }
  } else if (target.view === 'admin') {
    params.set('mode', target.tab)
  }
  const query = params.toString()
  return query ? `${path}?${query}` : path
}

/**
 * Where in the SPA we are — the Checkmk-native page model instead of
 * vue-router.
 *
 * State travels in the page query string (`maps.py?name=<map>`,
 * `maps.py?mode=<admin-tab>`) and transitions use the History API, mirroring the
 * Dashboard app (`dashboard/utils.ts` urlHandler). No hash, no reload.
 */
export class NavigationService {
  public readonly state: NavState = reactive(parse(window.location.search))

  private readonly onPopState = (): void => {
    Object.assign(this.state, parse(window.location.search))
  }

  public constructor() {
    window.addEventListener('popstate', this.onPopState)
  }

  /** Called when the app goes away, so a reconnect does not stack listeners. */
  public dispose(): void {
    window.removeEventListener('popstate', this.onPopState)
  }

  public navigate(target: NavTarget): void {
    const url = buildUrl(target)
    if (url !== window.location.pathname + window.location.search) {
      window.history.pushState({}, '', url)
    }
    this.onPopState()
  }

  public replace(target: NavTarget): void {
    window.history.replaceState({}, '', buildUrl(target))
    this.onPopState()
  }

  public href(target: NavTarget): string {
    return buildUrl(target)
  }
}
