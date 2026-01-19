/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/* eslint-disable indent */
import type { BaseType, Selection } from 'd3'
import { select as d3select, selectAll } from 'd3'
import $ from 'jquery'

import { FigureBase } from '@/modules/figures/cmk_figures'
import { TableFigure } from '@/modules/figures/cmk_table'

import type { NtopColumn } from './ntop_flows'

// TODO: Use library functions from number_format.js
const NTOPNG_MIN_VISUAL_VALUE = 0.005
export const ifid_dep = 'ifid_dependent'

export class interface_table extends TableFigure {
  _host_address!: string
  _vlanid!: string
  _ifid!: string
  set_host_address(host_address: string) {
    this._host_address = host_address
  }

  set_vlanid(vlanid: string) {
    this._vlanid = vlanid
  }

  set_ifid(ifid: string) {
    this._ifid = ifid
  }

  override initialize(debug?: boolean) {
    FigureBase.prototype.initialize.call(this, debug)
    this._table = this._div_selection
      .selectAll('.interface_table')
      .data([null])
      .join((enter) =>
        enter.append('table').classed('interface_table', true)
      ) as unknown as Selection<HTMLTableElement, unknown, BaseType, unknown>
  }

  override update_gui() {
    super.update_gui()
    const select = $('div.ntop').find(
      '#ntop_interface_choice.select2-enable, #ntop_vlan_choice.select2-enable'
    )
    const select2 = select.select2({
      dropdownAutoWidth: true,
      minimumResultsForSearch: 5
    })
    select2.on('select2:select', (event) => {
      this._change_post_url(d3select(event.target))
      this.scheduler.force_update()
    })
  }
  _change_post_url(select: Selection<Element, unknown, null, unknown>) {
    const name = select.property('name')
    const id = select.property('value')
    switch (name) {
      case 'ntop_interface_choice':
        this.set_ifid(id)
        break
      case 'ntop_vlan_choice':
        this.set_vlanid(id)
        break
      default:
        return
    }
    const host_body = this._host_address ? '&host_address=' + this._host_address : ''
    this.set_post_url_and_body(
      'ajax_ntop_interface_quickstats.py?vlanid=' + this._vlanid + '&ifid=' + this._ifid + host_body
    )
    selectAll('.' + ifid_dep)
      .data()
      // @ts-ignore
      .forEach((o) => o.set_ids(this._ifid, this._vlanid))
  }
}

export function bytes_to_volume(bytes: number) {
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  if (bytes == 0) return '0 Bytes'
  if (bytes > 0 && bytes < NTOPNG_MIN_VISUAL_VALUE) return '< ' + NTOPNG_MIN_VISUAL_VALUE + ' Bytes'
  const res = scale_value(bytes, sizes, 1024)
  return parseFloat(String(res[0])) + ' ' + res[1]
}

function scale_value(val: number, sizes: string[], scale: number) {
  if (val == 0) return [0, sizes[0]]
  let i = Math.floor(Math.log(val) / Math.log(scale))
  if (i < 0 || isNaN(i)) {
    i = 0
  } else if (i >= sizes.length) i = sizes.length - 1

  return [Math.round((val / Math.pow(scale, i)) * 10) / 10, sizes[i]]
}

export function seconds_to_time(seconds: number) {
  if (seconds < 1) {
    return '< 1 sec'
  }

  let days = Math.floor(seconds / 86400)
  const hours = Math.floor(seconds / 3600 - days * 24)
  const minutes = Math.floor(seconds / 60 - days * 1440 - hours * 60)
  const sec = seconds % 60
  let msg = ''
  const msg_array: string[] = []

  if (days > 0) {
    const years = Math.floor(days / 365)

    if (years > 0) {
      days = days % 365

      msg = years + ' year'
      if (years > 1) {
        msg += 's'
      }

      msg_array.push(msg)
      msg = ''
    }
    msg = days + ' day'
    if (days > 1) {
      msg += 's'
    }
    msg_array.push(msg)
    msg = ''
  }

  if (hours > 0) {
    if (hours < 10) msg = '0'
    msg += hours + ':'
  }

  if (minutes < 10) msg += '0'
  msg += minutes + ':'

  if (sec < 10) msg += '0'

  msg += sec
  msg_array.push(msg)
  return msg_array.join(', ')
}

export function add_columns_classes_to_nodes(
  selection: Selection<HTMLDivElement, unknown, BaseType, unknown>,
  columns: NtopColumn[]
) {
  selection
    .selectAll('tr')
    .selectAll('td')
    .each((_d, idx, nodes) => {
      const classes = columns[idx].classes
      if (!classes) return
      const node = d3select(nodes[idx])
      classes.forEach((classname) => {
        node.classed(classname, true)
      })
    })
}

export function add_classes_to_trs(
  selection: Selection<HTMLDivElement, unknown, BaseType, unknown>
) {
  selection.selectAll('tr').selectAll('a').classed('ntop_link', true).attr('target', '_blank')
  selection.select('thead tr').classed('header', true)
}
