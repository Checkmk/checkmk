/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { execute_javascript_by_object } from './utils'

//#   +--------------------------------------------------------------------+
//#   | Mouseover hover menu, used for performance graph popups            |
//#   '--------------------------------------------------------------------'

const HOVER_PORTAL_CLASS = 'cmk-hover-popup-portal'
let g_hover_menu: HTMLDivElement | null

export function hide() {
  if (!g_hover_menu) {
    return
  }

  const hover_menu = g_hover_menu
  g_hover_menu = null
  hover_menu.parentNode?.removeChild(hover_menu)
}

export function show(event_: MouseEvent, code: string) {
  add()
  update_content(code, event_)
}

export function add() {
  if (g_hover_menu) {
    return
  }

  g_hover_menu = document.createElement('div')
  g_hover_menu.setAttribute('id', 'hover_menu')
  g_hover_menu.className = 'hover_menu'

  hover_container().appendChild(g_hover_menu)
}

export function update_content(code: string, event_: MouseEvent) {
  if (!g_hover_menu) {
    return
  }

  /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
  g_hover_menu.innerHTML = code
  execute_javascript_by_object(g_hover_menu)
  update_position(event_)
}

// The content area starts where the navigation bar and a left-positioned sidebar end,
// so the popup never renders underneath them.
function content_area_left(): number {
  const content_area = document.getElementById('content_area')
  return content_area ? content_area.getBoundingClientRect().left : 0
}

// Position updates are triggered by the AJAX call response in graph_integration.js
export function update_position(event_: MouseEvent) {
  if (!g_hover_menu) {
    return
  }

  const hoverSpacer = 8
  const menu = g_hover_menu
  const vw = document.documentElement.clientWidth
  const vh = document.documentElement.clientHeight
  const minLeft = content_area_left() + hoverSpacer

  menu.style.visibility = 'hidden'
  menu.style.left = event_.clientX + hoverSpacer + 'px'
  menu.style.top = event_.clientY + hoverSpacer + 'px'

  if (event_.clientX + hoverSpacer + menu.clientWidth > vw) {
    if (menu.clientWidth + hoverSpacer <= event_.clientX) {
      menu.style.left = event_.clientX - menu.clientWidth - hoverSpacer + 'px'
    } else {
      menu.style.left = minLeft + 'px'
      menu.style.width = vw - minLeft - hoverSpacer + 'px'
    }
  }

  if (event_.clientY + hoverSpacer + menu.clientHeight > vh) {
    if (menu.clientHeight + hoverSpacer <= event_.clientY) {
      menu.style.top = event_.clientY - menu.clientHeight - hoverSpacer + 'px'
    } else {
      menu.style.top = hoverSpacer + 'px'
    }
  }

  menu.style.visibility = 'visible'
}

function hover_container(): HTMLDivElement {
  // Always use a fixed portal on document.body
  const existing = document.body.querySelector(`.${HOVER_PORTAL_CLASS}`)
  if (existing instanceof HTMLDivElement) return existing
  const portal = document.createElement('div')
  portal.className = HOVER_PORTAL_CLASS
  document.body.appendChild(portal)
  return portal
}
