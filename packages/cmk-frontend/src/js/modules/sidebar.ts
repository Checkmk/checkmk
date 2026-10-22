/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { call_ajax } from './ajax'
import {
  add_class,
  has_class,
  is_window_active,
  prevent_default_events,
  reload_whole_page,
  remove_class,
  update_contents
} from './utils'

/************************************************
 * misc sidebar stuff
 *************************************************/

export function toggle_sidebar() {
  const sidebar = document.getElementById('check_mk_sidebar')
  if (sidebar) {
    if (has_class(sidebar, 'folded')) unfold_sidebar()
    else fold_sidebar()
    window.dispatchEvent(new Event('resize'))
  }
}

export function fold_sidebar() {
  const sidebar = document.getElementById('check_mk_sidebar')
  if (sidebar) {
    add_class(sidebar, 'folded')
    call_ajax('sidebar_fold.py?fold=yes', { method: 'POST' })
  }
}

function unfold_sidebar() {
  const sidebar = document.getElementById('check_mk_sidebar')
  if (sidebar) {
    remove_class(sidebar, 'folded')
    call_ajax('sidebar_fold.py?fold=no', { method: 'POST' })
  }
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

export function virtual_host_tree_changed(field: HTMLSelectElement) {
  call_ajax('sidebar_ajax_tag_tree.py?tree_id=' + encodeURIComponent(field.value), {
    response_handler: () => refresh_single_snapin('tag_tree')
  })
}

export function virtual_host_tree_enter(path: string) {
  call_ajax('sidebar_ajax_tag_tree_enter.py?path=' + encodeURIComponent(path), {
    response_handler: () => refresh_single_snapin('tag_tree')
  })
}

export function refresh_single_snapin(name: string) {
  const event = new CustomEvent('sidebar-update-snapin-content', {
    detail: {
      name
    }
  })
  window.dispatchEvent(event)
}

/************************************************
 * WATO Foldertree (Standalone) snapin handling
 *************************************************/

/* Foldable Tree in snapin */
export function wato_tree_click(folderpath: string) {
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

  window.location.href = href
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
  const url = window.location
  const title = document.title
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

export function update_vue_snapin_contents(id: string, content: string) {
  const event = new CustomEvent('sidebar-new-snapin-content', {
    detail: {
      name: id.replace('snapin_', ''),
      content
    }
  })
  window.dispatchEvent(event)
}
