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

// The page content starts where the navigation bar, the sidebar and the page heading end, so the
// popup never renders underneath/above any of them. A page without a standard header still has the
// content area around it. One with neither / with a zero size container is bounded by the viewport
// alone.
function page_content_rect(): DOMRect {
  const content =
    document.getElementById('main_page_content') ?? document.getElementById('content_area')
  const rect = content?.getBoundingClientRect()
  if (rect && rect.width > 0 && rect.height > 0) {
    return rect
  }
  return new DOMRect(
    0,
    0,
    document.documentElement.clientWidth,
    document.documentElement.clientHeight
  )
}

// Position updates are triggered by the AJAX call response in graph_integration.js
export function update_position(event_: MouseEvent) {
  if (!g_hover_menu) {
    return
  }

  const hoverSpacer = 8
  const menu = g_hover_menu
  const vw = document.documentElement.clientWidth
  const content = page_content_rect()
  const spaceRight = content.right - (event_.clientX + hoverSpacer)
  const spaceLeft = event_.clientX - hoverSpacer - content.left

  // Default rendering to the right and downwards. Reset width, max-width and the justify-content
  // variable.
  menu.style.visibility = 'hidden'
  menu.style.width = ''
  menu.style.maxWidth = ''
  menu.style.left = event_.clientX + hoverSpacer + 'px'
  menu.style.right = 'auto'
  menu.style.top = event_.clientY + hoverSpacer + 'px'
  menu.style.removeProperty('--cmk-graph-group-justify-content')

  // Switch sides when the popup doesn't fit to the right and there's more space on the left.
  // If it doesn't fit either side it's shrunk into the roomier side via the maxWidth style.
  // We let it shrink instead of overflow to avoid any overlap with nav- or sidebar.
  if (menu.clientWidth > spaceRight && spaceLeft > spaceRight) {
    menu.style.right = vw - event_.clientX + hoverSpacer + 'px'
    menu.style.left = 'auto'
    menu.style.maxWidth = spaceLeft + 'px'
    // --cmk-graph-group-justify-content is consumed by GraphGroup.vue
    // We anchor the graph group to the right here so a wrapped group (multiple lines) is rendered
    // next to the cursor
    menu.style.setProperty('--cmk-graph-group-justify-content', 'flex-end')
  } else {
    menu.style.maxWidth = spaceRight + 'px'
  }

  // Too little room below: grow upwards from the page content's bottom, never past its top.
  // Taller than the page content, the popup overflows downwards out of the viewport.
  if (menu.clientHeight > content.height - (event_.clientY + hoverSpacer)) {
    menu.style.top = Math.max(content.bottom - menu.clientHeight - hoverSpacer, content.top) + 'px'
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
