/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  content_wrapper_size,
  execute_javascript_by_object,
  get_content_wrapper_object
} from './utils'

//#   +--------------------------------------------------------------------+
//#   | Mouseover hover menu, used for performance graph popups            |
//#   '--------------------------------------------------------------------'

type ContainerSize = { height: number | null; width: number | null }
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

// Position updates are triggered by the AJAX call response in graph_integration.js
export function update_position(event_: MouseEvent) {
  if (!g_hover_menu) {
    return
  }

  const hoverSpacer = 8

  // When inside the fixed portal, use viewport-relative clientX/clientY directly.
  if (g_hover_menu.closest(`.${HOVER_PORTAL_CLASS}`)) {
    update_position_fixed(event_, hoverSpacer)
    return
  }

  // document.body.scrollTop does not work in IE
  let scrollTop = document.body.scrollTop
    ? document.body.scrollTop
    : document.documentElement.scrollTop
  let scrollLeft = document.body.scrollLeft
    ? document.body.scrollLeft
    : document.documentElement.scrollLeft

  // Change scroll variables to SimpleBar container values if in place
  const scroll_container = g_hover_menu.closest('.simplebar-content-wrapper')
  if (scroll_container) {
    scrollTop = scroll_container.scrollTop
    scrollLeft = scroll_container.scrollLeft
  }

  let x = event_.clientX
  let y = event_.clientY
  const content_wrapper = get_content_wrapper_object()
  if (content_wrapper) {
    x = x - content_wrapper.offsetLeft
    y = y - content_wrapper.offsetTop
  }

  // hide the menu first to avoid an "up-then-over" visual effect
  g_hover_menu.style.visibility = 'hidden'
  g_hover_menu.style.left = scrollLeft + x + hoverSpacer + 'px'
  g_hover_menu.style.top = scrollTop + y + hoverSpacer + 'px'

  const hoverLeft = parseInt(g_hover_menu.style.left.replace('px', ''))
  const container_size = content_wrapper_size()
  let covers_full_width = false

  if (hoverLeft + g_hover_menu.clientWidth > scrollLeft + container_size.width!) {
    // The hover menu runs out of screen horizontally
    if (g_hover_menu.clientWidth + hoverSpacer <= x) {
      // Put the hover menu to the left of the cursor
      g_hover_menu.style.width = g_hover_menu.clientWidth + 'px'
      g_hover_menu.style.left = scrollLeft + x - g_hover_menu.clientWidth - hoverSpacer + 'px'
    } else {
      // Stretch the hover menu to full screen width
      stretch_to_full_width(g_hover_menu, container_size, scrollLeft, hoverSpacer)
      covers_full_width = true
    }
  }

  const hoverTop = parseInt(g_hover_menu.style.top.replace('px', ''))
  if (hoverTop + g_hover_menu.clientHeight > scrollTop + container_size.height!) {
    // The hover menu runs out of screen vertically
    if (g_hover_menu.clientHeight + hoverSpacer <= container_size.height!) {
      // The hover menu fits into the screen vertically
      if (covers_full_width && g_hover_menu.clientHeight + hoverSpacer < y) {
        // Put the hover menu with full screen width above the cursor
        g_hover_menu.style.top = scrollTop + y - g_hover_menu.clientHeight - hoverSpacer + 'px'
      } else if (!covers_full_width) {
        // Pull the hover menu as far to the top as needed
        g_hover_menu.style.top =
          scrollTop + container_size.height! - g_hover_menu.clientHeight - hoverSpacer + 'px'
      } else {
        stretch_to_full_width(g_hover_menu, container_size, scrollLeft, hoverSpacer)
      }
    } else {
      stretch_to_full_width(g_hover_menu, container_size, scrollLeft, hoverSpacer)
    }
  }

  g_hover_menu.style.visibility = 'visible'
}

function update_position_fixed(event_: MouseEvent, hoverSpacer: number) {
  const menu = g_hover_menu!
  const vw = document.documentElement.clientWidth
  const vh = document.documentElement.clientHeight

  menu.style.visibility = 'hidden'
  menu.style.left = event_.clientX + hoverSpacer + 'px'
  menu.style.top = event_.clientY + hoverSpacer + 'px'

  if (event_.clientX + hoverSpacer + menu.clientWidth > vw) {
    if (menu.clientWidth + hoverSpacer <= event_.clientX) {
      menu.style.left = event_.clientX - menu.clientWidth - hoverSpacer + 'px'
    } else {
      menu.style.left = hoverSpacer + 'px'
      menu.style.width = vw - 2 * hoverSpacer + 'px'
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

function stretch_to_full_width(
  _hover_menu: HTMLDivElement,
  container_size: ContainerSize,
  scrollLeft: number,
  hoverSpacer: number
) {
  g_hover_menu!.style.left = hoverSpacer + scrollLeft + 'px'
  g_hover_menu!.style.width = container_size.width! - 2 * hoverSpacer + 'px'
}

function hover_container() {
  // On dashboard pages, use a fixed portal on document.body to escape
  // stacking contexts and overflow containers that hide the tooltip.
  if (document.body.classList.contains('dashboard')) {
    return ensure_hover_portal()
  }

  // Return the simplebar wrapper div (if it exists) to avoid the default browser scrollbar for
  // long hover menu contents. If it doesn't exist try the content wrapper div. If that doesn't
  // exist either, fall back to the document body.
  const container = get_content_wrapper_object()
  if (!container) {
    return document.body
  }

  const simplebar_wrapper = container.getElementsByClassName('simplebar-content-wrapper')
  if (simplebar_wrapper.length == 0) {
    return container
  }
  return simplebar_wrapper[0]
}

function ensure_hover_portal(): HTMLDivElement {
  const existing = document.body.querySelector(`.${HOVER_PORTAL_CLASS}`)
  if (existing instanceof HTMLDivElement) return existing
  const portal = document.createElement('div')
  portal.className = HOVER_PORTAL_CLASS
  document.body.appendChild(portal)
  return portal
}
