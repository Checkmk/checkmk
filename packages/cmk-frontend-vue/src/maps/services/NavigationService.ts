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

/** What a map opens with, when the map list asks for more than the map. */
export type MapOpening = 'settings' | 'editor'

export type NavTarget =
  | { view: 'home' }
  | {
      view: 'map'
      name: string
      kiosk?: boolean
      preview?: boolean
      rotation?: string | null
      open?: MapOpening
    }
  | { view: 'admin'; tab: AdminTab }

export interface NavState {
  view: 'home' | 'map' | 'admin'
  name: string | null
  tab: AdminTab | null
  kiosk: boolean
  /** The rotation pool a map was opened in, which it rotates on within. */
  rotation: string | null
  preview: boolean
  open: MapOpening | null
}

/** Loads a URL as a new page; `replace` keeps the current history entry. */
export type PageLoader = (url: string, options: { replace: boolean }) => void

function loadPage(url: string, { replace }: { replace: boolean }): void {
  if (replace) {
    window.location.replace(url)
  } else {
    window.location.assign(url)
  }
}

const ADMIN_TABS: readonly AdminTab[] = ['icons']

function isAdminTab(value: string | null): value is AdminTab {
  return value !== null && (ADMIN_TABS as readonly string[]).includes(value)
}

function isMapOpening(value: string | null): value is MapOpening {
  return value === 'settings' || value === 'editor'
}

function parse(search: string): NavState {
  const params = new URLSearchParams(search)
  const mode = params.get('mode')
  const name = params.get('name')
  const kiosk = params.get('kiosk') === '1'
  const preview = params.get('preview') === '1'
  const open = params.get('open')
  if (isAdminTab(mode)) {
    return {
      view: 'admin',
      name: null,
      tab: mode,
      kiosk: false,
      preview: false,
      rotation: null,
      open: null
    }
  }
  if (name) {
    return {
      view: 'map',
      name,
      tab: null,
      kiosk,
      preview,
      rotation: params.get('rotation'),
      open: isMapOpening(open) ? open : null
    }
  }
  return {
    view: 'home',
    name: null,
    tab: null,
    kiosk: false,
    preview: false,
    rotation: null,
    open: null
  }
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
    if (target.rotation) {
      params.set('rotation', target.rotation)
    }
    if (target.open) {
      params.set('open', target.open)
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
 * `maps.py?mode=<admin-tab>`). Moving from one map to another uses the History
 * API, mirroring the Dashboard app (`dashboard/utils.ts` urlHandler). Every
 * other move loads the page: the map list carries the server's heading and page
 * menu and a map does not, so only a load keeps that chrome in step.
 */
export class NavigationService {
  public readonly state: NavState = reactive(parse(window.location.search))

  private readonly onPopState = (): void => {
    Object.assign(this.state, parse(window.location.search))
  }

  public constructor(private readonly load: PageLoader = loadPage) {
    window.addEventListener('popstate', this.onPopState)
  }

  /** Called when the app goes away, so a reconnect does not stack listeners. */
  public dispose(): void {
    window.removeEventListener('popstate', this.onPopState)
  }

  public navigate(target: NavTarget): void {
    const url = buildUrl(target)
    if (this.needsLoad(target)) {
      this.load(url, { replace: false })
      return
    }
    if (url !== window.location.pathname + window.location.search) {
      window.history.pushState({}, '', url)
    }
    this.onPopState()
  }

  public replace(target: NavTarget): void {
    const url = buildUrl(target)
    if (this.needsLoad(target)) {
      this.load(url, { replace: true })
      return
    }
    window.history.replaceState({}, '', url)
    this.onPopState()
  }

  private needsLoad(target: NavTarget): boolean {
    return target.view !== 'map' || this.state.view !== 'map'
  }

  public href(target: NavTarget): string {
    return buildUrl(target)
  }
}
