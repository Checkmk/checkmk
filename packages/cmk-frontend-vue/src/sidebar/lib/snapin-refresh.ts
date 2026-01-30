/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { SIDEBAR_UPDATE_SNAPIN_CONTENT_EVENT } from './constants'

export function refreshSidebarSnapin(snapinName: string): void {
  // If in an iframe, target the parent window; otherwise, target the current window.
  // This ensures the event is also dispatched properly once we don't use iframes anymore.
  const targetWindow = window.parent !== window ? window.parent : window

  const event = new CustomEvent(SIDEBAR_UPDATE_SNAPIN_CONTENT_EVENT, {
    detail: { name: snapinName }
  })

  targetWindow.dispatchEvent(event)
}
