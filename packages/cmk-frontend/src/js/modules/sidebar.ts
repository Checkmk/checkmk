/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type SimpleBar from 'simplebar'
import Swal from 'sweetalert2'

import { call_ajax } from './ajax'
import { close_popup } from './quicksearch'
import type { CMKAjaxReponse } from './types'
import {
  add_class,
  change_class,
  execute_javascript_by_object,
  get_button,
  has_class,
  is_window_active,
  prevent_default_events,
  reload_whole_page,
  remove_class,
  update_contents
} from './utils'

let g_content_loc: null | string = null
let g_scrollbar: SimpleBar | null | undefined = null

function update_content_location_if_accessible() {
  if (is_content_frame_accessible()) {
    update_content_location()
  }
}

export function initialize_sidebar() {
  setInterval(function () {
    update_content_location_if_accessible()
  }, 1000)
}

export function register_event_handlers() {
  window.addEventListener(
    'mousemove',
    function (e) {
      snapinDrag(e)
      return false
    },
    false
  )
}

// This ends drag scrolling when moving the mouse out of the sidebar
// frame while performing a drag scroll.
// This is no 100% solution. When moving the mouse out of browser window
// without moving the mouse over the edge elements the dragging is not ended.
export function register_edge_listeners(obj: Window | null) {
  // It is possible to open other domains in the content frame - don't register
  // the event in that case. It is not permitted by most browsers!
  if (!is_content_frame_accessible()) return

  const edge = obj ? obj : parent.frames[0]
  if (window.addEventListener !== null) edge.addEventListener('mousemove', on_mouse_leave, false)
  else edge.onmousemove = on_mouse_leave
}

function on_mouse_leave() {
  if (typeof close_popup != 'undefined') close_popup()
  snapinTerminateDrag()
  return false
}

/************************************************
 * snapin drag/drop code
 *************************************************/

let g_snapin_dragging: false | HTMLElement = false
let g_snapin_offset = [0, 0]
let g_snapin_start_pos = [0, 0]
let g_snapin_scroll_top = 0

export function snapin_start_drag(event: MouseEvent) {
  const target = event.target
  const button = get_button(event)

  // Skip calls when already dragging or other button than left mouse
  if (
    g_snapin_dragging !== false ||
    button != 'LEFT' ||
    (target instanceof HTMLElement && target.tagName != 'DIV')
  )
    return true

  event.cancelBubble = true
  g_snapin_dragging = (target as HTMLElement).parentNode as HTMLElement

  // Save relative offset of the mouse to the snapin title to prevent flipping on drag start
  g_snapin_offset = [
    event.clientY - g_snapin_dragging.offsetTop,
    event.clientX - g_snapin_dragging.offsetLeft
  ]
  g_snapin_start_pos = [event.clientY, event.clientX]
  g_snapin_scroll_top = document.getElementById('side_content')!.scrollTop

  // Disable the default events for all the different browsers
  return prevent_default_events(event)
}

function snapinDrag(event: MouseEvent) {
  if (g_snapin_dragging === false) return true

  // Is the mouse placed of the title bar of the snapin?
  // It can move e.g. if the scroll wheel is wheeled during dragging...

  // Drag the snapin
  add_class(g_snapin_dragging, 'dragging')
  let newTop = event.clientY - g_snapin_offset[0] - g_snapin_scroll_top
  newTop += document.getElementById('side_content')!.scrollTop
  g_snapin_dragging.style.top = newTop + 'px'
  g_snapin_dragging.style.left = event.clientX - g_snapin_offset[1] + 'px'

  // Refresh the drop marker
  removeSnapinDragIndicator()

  const line = document.createElement('div')
  line.setAttribute('id', 'snapinDragIndicator')
  const o = getSnapinTargetPos()
  if (o != null) {
    snapinAddBefore(o.parentNode!, o, line)
  } else {
    snapinAddBefore(g_snapin_dragging.parentNode!, null, line)
  }
  return true
}

function snapinAddBefore(par: Node, o: Node | null, add: HTMLElement) {
  if (o != null) {
    par.insertBefore(add, o)
  } else {
    par.insertBefore(add, document.getElementById('add_snapin'))
  }
}

function removeSnapinDragIndicator() {
  const o = document.getElementById('snapinDragIndicator')
  if (o) {
    o.parentNode?.removeChild(o)
  }
}

function snapinDrop(event: MouseEvent, targetpos: HTMLElement): boolean | void {
  if (g_snapin_dragging === false) return true

  // Reset properties
  remove_class(g_snapin_dragging, 'dragging')
  g_snapin_dragging.style.top = ''
  g_snapin_dragging.style.left = ''

  // Catch quick clicks without movement on the title bar
  // Don't reposition the object in this case.
  if (g_snapin_start_pos[0] == event.clientY && g_snapin_start_pos[1] == event.clientX) {
    return prevent_default_events(event)
  }

  const par = g_snapin_dragging.parentNode
  par!.removeChild(g_snapin_dragging)
  snapinAddBefore(par!, targetpos, g_snapin_dragging)

  // Now send the new information to the backend
  const thisId = g_snapin_dragging.id.replace('snapin_container_', '')

  let before = ''
  if (targetpos != null) before = '&before=' + targetpos.id.replace('snapin_container_', '')
  call_ajax('sidebar_move_snapin.py?name=' + thisId + before)
  refresh_single_snapin(thisId)
}

function snapinTerminateDrag(): true | void {
  if (g_snapin_dragging == false) return true
  removeSnapinDragIndicator()
  // Reset properties
  remove_class(g_snapin_dragging, 'dragging')
  g_snapin_dragging.style.top = ''
  g_snapin_dragging.style.left = ''
  g_snapin_dragging = false
}

export function snapin_stop_drag(event: Event) {
  if (!g_snapin_dragging) return

  removeSnapinDragIndicator()
  snapinDrop(event as MouseEvent, getSnapinTargetPos())
  g_snapin_dragging = false
}

function getDivChildNodes(node: Node) {
  const children: HTMLElement[] = []
  for (const child of node.childNodes as NodeListOf<HTMLElement>) {
    if (child.tagName === 'DIV') {
      children.push(child)
    }
  }
  return children
}

function getSnapinList() {
  const l: HTMLElement[] = []
  g_snapin_dragging = g_snapin_dragging as HTMLElement
  for (const child of getDivChildNodes(g_snapin_dragging.parentNode!)) {
    // Skip non snapin objects and the currently dragged object
    const id = child.id
    if (id && id.substr(0, 7) == 'snapin_' && id != g_snapin_dragging.id) {
      l.push(child)
    }
  }
  return l
}

function getSnapinCoords(obj: HTMLElement) {
  const snapinTop = (g_snapin_dragging as HTMLElement).offsetTop
  // + document.getElementById("side_content").scrollTop;

  let bottomOffset = obj.offsetTop + obj.clientHeight - snapinTop
  if (bottomOffset < 0) bottomOffset = -bottomOffset

  let topOffset = obj.offsetTop - snapinTop
  if (topOffset < 0) topOffset = -topOffset

  let offset = topOffset
  let corner = 0
  if (bottomOffset < topOffset) {
    offset = bottomOffset
    corner = 1
  }

  return [bottomOffset, topOffset, offset, corner]
}

function getSnapinTargetPos() {
  const childs = getSnapinList()
  let objId = -1
  let objCorner = -1

  // Find the nearest snapin to current left/top corner of
  // the currently dragged snapin
  for (let i = 0; i < childs.length; i++) {
    const child = childs[i]

    // Initialize with the first snapin in the list
    if (objId === -1) {
      objId = i
      const coords = getSnapinCoords(child as HTMLElement)
      objCorner = coords[3]
      continue
    }

    // First check which corner is closer. Upper left or
    // the bottom left.
    const curCoords = getSnapinCoords(childs[objId] as HTMLElement)
    const newCoords = getSnapinCoords(child as HTMLElement)

    // Is the upper left corner closer?
    if (newCoords[2] < curCoords[2]) {
      objCorner = newCoords[3]
      objId = i
    }
  }

  // Is the dragged snapin dragged above the first one?
  return objId === 0 && objCorner === 0 ? childs[0] : childs[objId + 1]
}

/************************************************
 * misc sidebar stuff
 *************************************************/

// Checks if the sidebar can access the content frame. It might be denied
// by the browser since it blocks cross domain access.
export function is_content_frame_accessible() {
  try {
    parent.frames[0].document
    return true
  } catch (e) {
    return false
  }
}

export function update_content_location() {
  // initialize the original title
  //@ts-ignore
  if (typeof window.parent['orig_title'] == 'undefined') {
    //@ts-ignore
    window.parent['orig_title'] = window.parent.document.title
  }

  const content_frame = parent.frames[0]

  // Change the title to add the frame title to reflect the
  // title of the content URL title (window title or tab title)
  let page_title
  if (content_frame.document.title != '') {
    page_title =
      //@ts-ignore
      window.parent['orig_title'] + ' - ' + content_frame.document.title
  } else {
    //@ts-ignore
    page_title = window.parent['orig_title']
  }
  window.parent.document.title = page_title

  // Construct the URL to be called on page reload
  const parts = window.parent.location.pathname.split('/')
  parts.pop()
  const cmk_path = parts.join('/')
  const rel_url =
    content_frame.location.pathname + content_frame.location.search + content_frame.location.hash
  const index_url = cmk_path + '/index.py?start_url=' + encodeURIComponent(rel_url)

  if (window.parent.history.replaceState) {
    if (rel_url && rel_url != 'blank') {
      // Update the URL to be called on reload, e.g. via F5, to switch to exactly this URL
      window.parent.history.replaceState({}, page_title, index_url)

      // only update the internal flag var if the url was not blank and has been updated
      //otherwise try again on next scheduler run
      g_content_loc = content_frame.document.location.href
    }
  } else {
    // Only a browser without history.replaceState support reaches this. Sadly
    // we have no F5/reload fix for them...
    g_content_loc = content_frame.document.location.href
  }
}

const g_scrolling = true

export function scroll_window(speed: number) {
  const c = document.getElementById('side_content')

  if (g_scrolling) {
    c!.scrollTop += speed
    /* eslint-disable-next-line no-implied-eval -- Highlight existing violations CMK-17846 */
    setTimeout('cmk.sidebar.scroll_window(' + speed + ')', 10)
  }
}

export function toggle_sidebar() {
  const sidebar = document.getElementById('check_mk_sidebar')
  if (has_class(sidebar, 'folded')) unfold_sidebar()
  else fold_sidebar()
}

export function fold_sidebar() {
  const sidebar = document.getElementById('check_mk_sidebar')
  add_class(sidebar, 'folded')
  const button = document.getElementById('side_fold')
  add_class(button, 'folded')

  call_ajax('sidebar_fold.py?fold=yes', { method: 'POST' })
}

function unfold_sidebar() {
  const sidebar = document.getElementById('check_mk_sidebar')
  remove_class(sidebar, 'folded')
  const button = document.getElementById('side_fold')
  remove_class(button, 'folded')

  call_ajax('sidebar_fold.py?fold=no', { method: 'POST' })
}

//
// Sidebar ajax stuff
//

// The refresh snapins do reload after a defined amount of time
let refresh_snapins: string[][] = []
// The restart snapins are notified about the restart of the nagios instance(s)
let restart_snapins: string[] = []
// Snapins that only have to be reloaded on demand
let static_snapins: string[] = []
// Contains a timestamp which holds the time of the last nagios restart handling
let sidebar_restart_time: number | null = null
// Configures the number of seconds to reload all snapins which request it
let sidebar_update_interval: number | null = null

export function add_snapin(name: string) {
  call_ajax('sidebar_ajax_add_snapin.py?name=' + name, {
    method: 'POST',
    response_handler: function (_data: any, response: string) {
      const data = JSON.parse(response)
      if (data.result_code !== 0) {
        return
      }

      const result = data.result

      if (result.refresh) {
        const entry: [string, string] = [result.name, result.url]
        if (refresh_snapins.indexOf(entry) === -1) {
          refresh_snapins.push(entry)
        }
      }

      if (result.restart) {
        const entry = result.name
        if (restart_snapins.indexOf(entry) === -1) {
          restart_snapins.push(entry)
        }
      }

      if (!result.refresh && !result.restart) {
        const entry = result.name
        if (static_snapins.indexOf(entry) === -1) {
          static_snapins.push(entry)
        }
      }

      const sidebar_content = g_scrollbar?.getContentElement()
      if (sidebar_content) {
        const tmp_container = document.createElement('div')
        /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
        tmp_container.innerHTML = result.content

        const add_button = sidebar_content.lastChild as HTMLElement
        while (tmp_container.childNodes.length) {
          const tmp = tmp_container.childNodes[0] as HTMLElement
          add_button.insertAdjacentElement('beforebegin', tmp)

          // The object specific JS must be called after the object was inserted.
          // Otherwise JS code that works on DOM objects (e.g. the quicksearch snapin
          // registry) cannot find these objects.
          execute_javascript_by_object(tmp)
        }
      }

      const add_snapin_page = window.frames[0] ? window.frames[0].document : document
      const preview = add_snapin_page.getElementById('snapin_container_' + name)
      if (preview) {
        const container = preview.parentElement?.parentElement
        container?.remove()
      }
    }
  })
}

// Removes the snapin from the current sidebar and informs the server for persistance
export function remove_sidebar_snapin(oLink: HTMLButtonElement, url: string) {
  const container = oLink.parentNode!.parentNode as HTMLElement
  const id = container.id.replace('snapin_container_', '')

  call_ajax(url, {
    handler_data: 'snapin_' + id,
    response_handler: function (id: string) {
      remove_snapin(id)
    },
    method: 'POST'
  })
}

// Removes a snapin from the sidebar without reloading anything
function remove_snapin(id: string) {
  const container = document.getElementById(id)!.parentNode
  const myparent = container!.parentNode
  myparent!.removeChild(container!)

  const name = id.replace('snapin_', '')

  //TODO: fix bug, see: https://review.lan.tribe29.com/c/check_mk/+/54277
  // refresh_index always returns -1 because name is a string and indexOf expects
  // [string, string] element. so the to be deleted element is never deleted from
  // refresh_snapins array.
  //@ts-ignore
  const refresh_index = refresh_snapins.indexOf(name)
  if (refresh_index !== -1) {
    refresh_snapins.splice(refresh_index, 1)
  }

  const restart_index = restart_snapins.indexOf(name)
  if (restart_index !== -1) {
    restart_snapins.splice(refresh_index, 1)
  }

  const static_index = static_snapins.indexOf(name)
  if (static_index !== -1) {
    static_snapins.splice(static_index, 1)
  }

  // reload main frame if it is currently displaying the "add snapin" page
  if (parent.frames[0]) {
    const href = encodeURIComponent(parent.frames[0].location.toString())
    if (href.indexOf('sidebar_add_snapin.py') > -1) parent.frames[0].location.reload()
  }
}

export function toggle_sidebar_snapin(oH2: HTMLElement, url: string, imgId: string) {
  // oH2 is a <b> if it is the snapin title otherwise it is the minimize button.
  const childs = oH2.parentNode!.parentNode!.childNodes as NodeListOf<HTMLElement>

  let oContent: HTMLElement, oHead: HTMLElement
  const oImg: HTMLElement | null = document.getElementById(imgId)
  for (const i in childs) {
    const child = childs[i]
    if (child.tagName == 'DIV' && child.className == 'content') oContent = child
    else if (
      child.tagName == 'DIV' &&
      (child.className == 'head open' || child.className == 'head closed')
    )
      oHead = child
  }

  // FIXME: Does oContent really exist?
  const closed = oContent!.style.display == 'none'
  const snapinContainer = oH2.parentNode!.parentNode
  const showMore = snapinContainer!.querySelector('.moresnapin') as HTMLElement
  const closeSnapin = snapinContainer!.querySelector('.closesnapin') as HTMLElement
  if (closed) {
    if (showMore) {
      remove_class(showMore, 'hidden')
    }
    remove_class(closeSnapin, 'hidden')
    oContent!.style.display = 'block'
    change_class(oHead!, 'closed', 'open')
    change_class(oImg!, 'closed', 'open')
  } else {
    if (showMore) {
      add_class(showMore, 'hidden')
    }
    add_class(closeSnapin, 'hidden')
    oContent!.style.display = 'none'
    change_class(oHead!, 'open', 'closed')
    change_class(oImg!, 'open', 'closed')
  }
  /* make this persistent -> save */
  call_ajax(url + (closed ? 'open' : 'closed'), { method: 'POST' })
}

// TODO this is managed code, should be moved to separate package
export function switch_customer(customer_id: string, switch_state: string) {
  call_ajax('switch_customer.py?_customer_switch=' + customer_id + ':' + switch_state, {
    response_handler: reload_whole_page,
    handler_data: null
  })
}

export function switch_site(url: string) {
  call_ajax(url, {
    method: 'POST',
    response_handler: reload_whole_page,
    handler_data: null
  })
}

function bulk_update_contents(ids: string[], codes: string) {
  /* eslint-disable-next-line no-eval -- Highlight existing violations CMK-17846 */
  codes = eval(codes)
  for (let i = 0; i < ids.length; i++) {
    if (restart_snapins.indexOf(ids[i].replace('snapin_', '')) !== -1) {
      // Snapins which rely on the restart time of nagios receive
      // an empty code here when nagios has not been restarted
      // since sidebar rendering or last update, skip it
      if (codes[i] !== '') {
        update_contents(ids[i], codes[i])
        sidebar_restart_time = Math.floor(new Date().getTime() / 1000)
      }
    } else {
      update_contents(ids[i], codes[i])
    }
  }
}

let g_seconds_to_update: null | number = null
let g_sidebar_scheduler_timer: null | number = null
let g_sidebar_full_reload = false

export function refresh_single_snapin(name: string) {
  const event = new CustomEvent('sidebar-update-snapin-content', {
    detail: {
      name
    }
  })
  window.dispatchEvent(event)
}

export function reset_sidebar_scheduler() {
  if (g_sidebar_scheduler_timer !== null) {
    clearTimeout(g_sidebar_scheduler_timer)
    g_sidebar_scheduler_timer = null
  }
  g_seconds_to_update = 1
  g_sidebar_full_reload = true
  execute_sidebar_scheduler()
}

export function execute_sidebar_scheduler() {
  g_seconds_to_update =
    g_seconds_to_update !== null ? g_seconds_to_update - 1 : sidebar_update_interval

  // Stop reload of the snapins in case the browser window / tab is not visible
  // for the user. Retry after short time.
  if (!is_window_active()) {
    g_sidebar_scheduler_timer = window.setTimeout(function () {
      execute_sidebar_scheduler()
    }, 250)
    return
  }

  const to_be_updated: string[] = []

  let url
  for (let i = 0; i < refresh_snapins.length; i++) {
    const name = refresh_snapins[i][0]
    if (refresh_snapins[i][1] !== '') {
      // Special handling for snapins like the nagvis maps snapin which request
      // to be updated from a special URL, use direct update of those snapins
      // from this url
      url = refresh_snapins[i][1]

      if (g_seconds_to_update && g_seconds_to_update <= 0) {
        call_ajax(url, {
          response_handler: update_contents,
          handler_data: 'snapin_' + name
        })
      }
    } else {
      // Internal update handling, use bulk update
      to_be_updated.push(name)
    }
  }

  if (g_sidebar_full_reload) {
    g_sidebar_full_reload = false
    for (const name of static_snapins) {
      to_be_updated.push(name)
    }
  }

  // Are there any snapins to be bulk updated?
  if (to_be_updated.length > 0 && g_seconds_to_update && g_seconds_to_update <= 0) {
    url = 'sidebar_snapin.py?names=' + to_be_updated.join(',')
    if (sidebar_restart_time !== null) url += '&since=' + sidebar_restart_time

    const ids: string[] = [],
      len = to_be_updated.length
    for (let i = 0; i < len; i++) {
      ids.push('snapin_' + to_be_updated[i])
    }

    call_ajax(url, {
      response_handler: bulk_update_contents,
      handler_data: ids
    })
  }

  if (g_sidebar_notify_interval !== null) {
    if (g_seconds_to_update == 0) {
      update_messages()
      if (g_may_ack) {
        update_unack_incomp_werks()
      }
    }
  }

  // Detect page changes and re-register the mousemove event handler
  // in the content frame. another bad hack ... narf
  if (is_content_frame_accessible() && g_content_loc != parent.frames[0].document.location.href) {
    register_edge_listeners(parent.frames[0])
    update_content_location()
  }

  if (g_seconds_to_update && g_seconds_to_update <= 0) g_seconds_to_update = sidebar_update_interval

  g_sidebar_scheduler_timer = window.setTimeout(function () {
    execute_sidebar_scheduler()
  }, 1000)
}

/************************************************
 * Save/Restore scroll position
 *************************************************/

// TODO: remove expiredays. this is either a null or number, though
//  it is been used only one time as null and when we add date to null
//  we get a very weird result so to be safer it's better to delete it
function setCookie(cookieName: string, value: number, expiredays: null | number) {
  const exdate = new Date()
  exdate.setDate(exdate.getDate() + (expiredays ?? 0))
  document.cookie =
    cookieName +
    '=' +
    encodeURIComponent(value) +
    (expiredays == null ? '' : ';expires=' + exdate.toUTCString() + ';SameSite=Lax')
}

function getCookie(cookieName: string) {
  if (document.cookie.length == 0) return null

  let cookieStart = document.cookie.indexOf(cookieName + '=')
  if (cookieStart == -1) return null

  cookieStart = cookieStart + cookieName.length + 1
  let cookieEnd = document.cookie.indexOf(';', cookieStart)
  if (cookieEnd == -1) cookieEnd = document.cookie.length
  return decodeURIComponent(document.cookie.substring(cookieStart, cookieEnd))
}

export function initialize_scroll_position() {
  if (!g_scrollbar) return
  const scrollPosFromCookie = getCookie('sidebarScrollPos')
  const scrollPos: number = scrollPosFromCookie ? parseInt(scrollPosFromCookie) : 0
  // 2531: Object is possibly 'null'
  // @ts-ignore
  g_scrollbar.getScrollElement().scrollTop = scrollPos
}

function store_scroll_position() {
  setCookie(
    'sidebarScrollPos',
    // 2345: Argument of type 'number | undefined' is not assignable to
    // parameter of type 'number'
    // @ts-ignore
    g_scrollbar!.getScrollElement()?.scrollTop,
    null
  )
}

/************************************************
 * WATO Folders snapin handling
 *************************************************/

// FIXME: Make this somehow configurable - use the start url?
let g_last_view = 'dashboard.py?name=main'
let g_last_folder = ''

// highlight the followed link (when both needed snapins are available)
function highlight_link(link_obj: HTMLElement, container_id: string) {
  const this_snapin = document.getElementById(container_id)
  let other_snapin
  if (container_id == 'snapin_container_wato_folders')
    other_snapin = document.getElementById('snapin_container_views')
  else other_snapin = document.getElementById('snapin_container_wato_folders')

  if (this_snapin && other_snapin) {
    let links: HTMLCollectionOf<HTMLElement>
    if (this_snapin.getElementsByClassName)
      links = this_snapin.getElementsByClassName('link') as HTMLCollectionOf<HTMLElement>
    else links = document.getElementsByClassName('link') as HTMLCollectionOf<HTMLElement>

    for (let i = 0; i < links.length; i++) {
      links[i].style.fontWeight = 'normal'
    }

    link_obj.style.fontWeight = 'bold'
  }
}

export function wato_folders_clicked(link_obj: HTMLElement, folderpath: string) {
  g_last_folder = folderpath
  highlight_link(link_obj, 'snapin_container_wato_folders')
  parent.frames[0].location = g_last_view + '&wato_folder=' + encodeURIComponent(g_last_folder)
}

export function wato_views_clicked(link_obj: HTMLLinkElement) {
  g_last_view = link_obj.href

  highlight_link(link_obj, 'snapin_container_views')
  highlight_link(link_obj, 'snapin_container_dashboards')

  if (g_last_folder != '') {
    // Navigate by using javascript, cancel following the default link
    parent.frames[0].location = g_last_view + '&wato_folder=' + encodeURIComponent(g_last_folder)
    return false
  } else {
    // Makes use the url stated in href attribute
    return true
  }
}

/************************************************
 * WATO Foldertree (Standalone) snapin handling
 *************************************************/

/* Foldable Tree in snapin */
export function wato_tree_click(_link_obj: string, folderpath: string) {
  const topic = (document.getElementById('topic') as HTMLInputElement).value
  const target = (document.getElementById('target_' + topic) as HTMLInputElement).value

  let href
  if (target.substr(0, 9) == 'dashboard') {
    const dashboard_name = target.substr(10, target.length)
    href = 'dashboard.py?name=' + encodeURIComponent(dashboard_name)
  } else {
    href = 'view.py?view_name=' + encodeURIComponent(target)
  }

  href += '&wato_folder=' + encodeURIComponent(folderpath)

  parent.frames[0].location = href
}

export function wato_tree_topic_changed(topic_field: HTMLSelectElement) {
  // First toggle the topic dropdown field
  const topic = topic_field.value

  // Hide all select fields but the wanted one
  const select_fields = document.getElementsByTagName('select')
  for (let i = 0; i < select_fields.length; i++) {
    if (select_fields[i].id && select_fields[i].id.substr(0, 7) == 'target_') {
      select_fields[i].selectedIndex = -1
      if (select_fields[i].id == 'target_' + topic) {
        select_fields[i].style.display = 'inline'
      } else {
        select_fields[i].style.display = 'none'
      }
    }
  }

  // Then send the info to python code via ajax call for persistance
  call_ajax('ajax_set_foldertree.py', {
    method: 'POST',
    post_data: 'topic=' + encodeURIComponent(topic) + '&target='
  })
}

export function wato_tree_target_changed(target_field: HTMLSelectElement) {
  const topic = target_field.id.substr(7, target_field.id.length)
  const target = target_field.value

  // Send the info to python code via ajax call for persistance
  call_ajax('ajax_set_foldertree.py', {
    method: 'POST',
    post_data: 'topic=' + encodeURIComponent(topic) + '&target=' + encodeURIComponent(target)
  })
}

/************************************************
 * Event console site selection
 *************************************************/

export function set_snapin_site(event: Event, ident: string, select_field: HTMLSelectElement) {
  call_ajax(
    'sidebar_ajax_set_snapin_site.py?ident=' +
      encodeURIComponent(ident) +
      '&site=' +
      encodeURIComponent(select_field.value),
    {
      response_handler: function (_handler_data: string, _response_body: any) {
        refresh_single_snapin(ident)
      }
    }
  )
  return prevent_default_events(event)
}

/************************************************
 * Render the nagvis snapin contents
 *************************************************/

export function fetch_nagvis_snapin_contents() {
  const nagvis_snapin_update_interval = 30

  // Stop reload of the snapin content in case the browser window / tab is
  // not visible for the user. Retry after short time.
  if (!is_window_active()) {
    setTimeout(function () {
      fetch_nagvis_snapin_contents()
    }, 250)
    return
  }

  // Needs to be fetched via JS from NagVis because it needs to
  // be done in the user context.
  const nagvis_url = '../nagvis/server/core/ajax_handler.php?mod=Multisite&act=getMaps'
  call_ajax(nagvis_url, {
    add_ajax_id: false,
    response_handler: function (_unused_handler_data: any, ajax_response: string) {
      // Then hand over the data to the python code which is responsible
      // to render the data.
      call_ajax('ajax_nagvis_maps_snapin.py', {
        method: 'POST',
        add_ajax_id: false,
        post_data: 'request=' + encodeURIComponent(ajax_response),
        response_handler: function (_unused_handler_data: any, snapin_content_response: string) {
          update_vue_snapin_contents('snapin_nagvis_maps', snapin_content_response)
        }
      })

      setTimeout(function () {
        fetch_nagvis_snapin_contents()
      }, nagvis_snapin_update_interval * 1000)
    },
    error_handler: function (_unused: any, status_code: number) {
      const msg = document.createElement('div')
      msg.classList.add('message', 'error')
      /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
      msg.innerHTML = 'Failed to update NagVis maps: ' + status_code
      update_contents('snapin_nagvis_maps', msg.outerHTML)

      setTimeout(function () {
        fetch_nagvis_snapin_contents()
      }, nagvis_snapin_update_interval * 1000)
    },
    method: 'GET'
  })
}

/************************************************
 * Bookmark snapin
 *************************************************/

export function add_bookmark() {
  const url = parent.frames[0].location
  const title = parent.frames[0].document.title
  call_ajax('add_bookmark.py', {
    add_ajax_id: false,
    response_handler: update_vue_snapin_contents,
    handler_data: 'snapin_bookmarks',
    method: 'POST',
    post_data: 'title=' + encodeURIComponent(title) + '&url=' + encodeURIComponent(url.toString())
  })
}

/************************************************
 * Speedometer snapin
 *************************************************/

let g_needle_timeout: null | number = null

interface Speedometer {
  scheduled_rate: number
  program_start: number
  percentage: number
  last_perc: number
  title?: string
}

export function speedometer_show_speed(
  last_perc: number,
  program_start: number,
  scheduled_rate: number
) {
  const url =
    'sidebar_ajax_speedometer.py' +
    '?last_perc=' +
    last_perc +
    '&scheduled_rate=' +
    scheduled_rate +
    '&program_start=' +
    program_start

  call_ajax(url, {
    response_handler: function (handler_data: Speedometer, response_body: string) {
      let data: Speedometer
      try {
        data = JSON.parse(response_body)

        let oDiv = document.getElementById('speedometer')

        // Terminate reschedule when the speedometer div does not exist anymore
        // (e.g. the snapin has been removed)
        if (!oDiv) return

        oDiv.title = String(data.title)
        oDiv = document.getElementById('speedometerbg')
        oDiv!.title = String(data.title)

        move_needle(data.last_perc, data.percentage) // 50 * 100ms = 5s = refresh time
      } catch (ie) {
        // Ignore errors during re-rendering. Proceed with reschedule...
        data = handler_data
      }

      setTimeout(
        (function (data) {
          return function () {
            speedometer_show_speed(data.percentage, data.program_start, data.scheduled_rate)
          }
        })(data),
        5000
      )
    },
    error_handler: function (handler_data: Speedometer, _status_code: number, _error_msg: string) {
      setTimeout(
        (function (data: Speedometer) {
          return function () {
            return speedometer_show_speed(data.percentage, data.program_start, data.scheduled_rate)
          }
        })(handler_data),
        5000
      )
    },
    method: 'GET',
    handler_data: {
      percentage: last_perc,
      last_perc: last_perc,
      program_start: program_start,
      scheduled_rate: scheduled_rate
    }
  })
}

function show_speed(percentage: number) {
  const canvas = document.getElementById('speedometer') as HTMLCanvasElement
  if (!canvas) return

  const context = canvas.getContext('2d')
  if (!context) return

  if (percentage > 100.0) percentage = 100.0
  const orig_x = 115
  const orig_y = 165
  const angle_0 = 225.0
  const angle_100 = 314.0
  const angle = angle_0 + ((angle_100 - angle_0) * percentage) / 100.0
  const angle_rad = (angle / 360.0) * Math.PI * 2
  const length = 115
  const end_x = orig_x + Math.cos(angle_rad) * length
  const end_y = orig_y + Math.sin(angle_rad) * length

  context.clearRect(0, 0, 240, 146)
  context.beginPath()
  context.moveTo(orig_x, orig_y)
  context.lineTo(end_x, end_y)
  context.closePath()
  context.shadowOffsetX = 2
  context.shadowOffsetY = 2
  context.shadowBlur = 2
  if (percentage < 80.0) context.strokeStyle = '#FF3232'
  else if (percentage < 95.0) context.strokeStyle = '#FFFE44'
  else context.strokeStyle = '#13D389'
  context.lineWidth = 3
  context.stroke()
}

function move_needle(from_perc: number, to_perc: number) {
  const new_perc = from_perc * 0.9 + to_perc * 0.1

  show_speed(new_perc)

  if (g_needle_timeout != null) clearTimeout(g_needle_timeout)

  g_needle_timeout = window.setTimeout(
    (function (new_perc, to_perc) {
      return function () {
        move_needle(new_perc, to_perc)
      }
    })(new_perc, to_perc),
    50
  )
}

/************************************************
 * Popup Message Handling
 *************************************************/

// integer representing interval in seconds or <null> when disabled.
let g_sidebar_notify_interval: null | number
let g_may_ack = false

export function init_messages_and_werks(interval: null | number, may_ack: boolean) {
  g_sidebar_notify_interval = interval
  create_initial_ids('user', 'messages', 'user_message.py')
  create_initial_ids('changes', 'changes', 'wato.py?mode=changelog')

  // Are there pending messages? Render the initial state of
  // trigger button
  update_messages()

  g_may_ack = may_ack
  if (!may_ack) {
    return
  }

  create_initial_ids('help', 'werks', 'change_log.py?show_unack=1&wo_compatibility=3')
  update_unack_incomp_werks()
}

interface AjaxSidebarGetMessages {
  popup_messages: { id: string; text: string }[]
  hint_messages: {
    type: string
    title: string
    text: string
    count: number
  }
}

function handle_update_messages(_data: any, response_text: string) {
  const response: CMKAjaxReponse<AjaxSidebarGetMessages> = JSON.parse(response_text)
  if (response.result_code !== 0) {
    return
  }
  const result = response.result
  const messages_text = result.hint_messages.text
  const messages_title = result.hint_messages.title
  const messages_count = result.hint_messages.count

  update_message_trigger(messages_text, messages_count)
  result.popup_messages.forEach((msg) => {
    Swal.fire({
      icon: 'info',
      title: messages_title,
      text: msg.text
    })
    mark_message_read(msg.id)
  })
}

function update_messages() {
  // retrieve new messages
  call_ajax('ajax_sidebar_get_messages.py', {
    response_handler: handle_update_messages
  })
}

export function update_message_trigger(msg_text: string, msg_count: number) {
  const l = document.getElementById('messages_label')
  if (l) {
    if (msg_count === 0) {
      l.style.display = 'none'
      return
    }

    l.innerText = msg_count.toString()
    l.style.display = 'inline'
  }

  const user_messages = document.getElementById('messages_link_to')
  if (user_messages) {
    const text_content = msg_count + ' ' + msg_text
    // We need the <a> tag where the current text is stored
    const popup_link = document.querySelector('#user_topic_usermessages ul li a')!
    // We only need the initial text part, excluding the already added text_content.
    // Otherwise it would added on each loop
    const popup_text = popup_link.textContent!.substring(0, 17)
    // Construct new text for the GUI hint
    popup_link.innerHTML = `${popup_text} <span class="new_msg">${text_content}</span>`
  }
}

function mark_message_read(msg_id: string) {
  call_ajax('sidebar_message_read.py?id=' + msg_id)
}

interface AjaxSidebarGetUnackIncompWerks {
  count: number
  text: string
  tooltip: string
}

function handle_update_unack_incomp_werks(_data: any, response_text: string) {
  const response: CMKAjaxReponse<AjaxSidebarGetUnackIncompWerks> = JSON.parse(response_text)
  if (response.result_code !== 0) {
    return
  }
  const result = response.result
  update_werks_trigger(result.count, result.text, result.tooltip)
}

function update_unack_incomp_werks() {
  // retrieve number of unacknowledged incompatible werks
  call_ajax('ajax_sidebar_get_unack_incomp_werks.py', {
    response_handler: handle_update_unack_incomp_werks
  })
}

export function update_werks_trigger(werks_count: number, text: string, tooltip: string) {
  const l = document.getElementById('werks_label')!
  if (werks_count === 0) {
    l.style.display = 'none'
    return
  }

  l.innerText = werks_count.toString()
  l.style.display = 'inline'

  const werks_link = document.getElementById('werks_link_to')
  if (werks_link) {
    werks_link.textContent = text
    werks_link.setAttribute('title', tooltip.toString())
  }
}
function create_initial_ids(menu: string, what: string, start_url: string) {
  const main_menu_help_div = document.getElementById('popup_trigger_main_menu_' + menu)!.firstChild
  const help_div = main_menu_help_div!.childNodes[2]

  const l = document.createElement('span')
  l.setAttribute('id', what + '_label')
  l.style.display = 'none'
  main_menu_help_div?.insertBefore(l, help_div)

  // Also update popup content
  const info_line_span = document.getElementById('info_line_' + menu)
  const span = document.createElement('span')
  span.setAttribute('id', what + '_link')
  const a = document.createElement('a')
  a.href = 'index.py?start_url=' + start_url
  a.setAttribute('id', what + '_link_to')
  span.appendChild(a)
  info_line_span?.insertAdjacentElement('beforebegin', span)
}

/************************************************
 * user menu callbacks
 *************************************************/

// for quick access options in user menu

export function toggle_user_attribute(mode: string) {
  call_ajax(mode, {
    method: 'POST',
    response_handler: function (_handler_data: any, ajax_response: string) {
      const data = JSON.parse(ajax_response)
      if (data.result_code == 0) {
        reload_whole_page()
      }
    }
  })
}

export function update_vue_snapin_contents(id: string, content: string) {
  const event = new CustomEvent('sidebar-new-snapin-content', {
    detail: {
      name: id.replace('snapin_', ''),
      content
    }
  })
  window.dispatchEvent(event)
}
