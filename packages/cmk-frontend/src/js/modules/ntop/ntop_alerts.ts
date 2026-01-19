/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import crossfilter, { Crossfilter, type Dimension } from 'crossfilter2'
import { BaseType, D3BrushEvent, Selection, select as d3select } from 'd3'
import { select, selectAll } from 'd3'
import * as d3 from 'd3'
import $ from 'jquery'

import { FigureBase } from '@/modules/figures/cmk_figures'
import { Tab, TabsBar } from '@/modules/figures/cmk_tabs'
import type { FigureData } from '@/modules/figures/figure_types'
import { MultiDataFetcher } from '@/modules/figures/multi_data_fetcher'

import { FlowDashletDataChoice, FlowData, NtopColumn } from './ntop_flows'
import {
  add_classes_to_trs,
  add_columns_classes_to_nodes,
  ifid_dep,
  seconds_to_time
} from './ntop_utils'

export class NtopAlertsTabBar extends TabsBar {
  _cmk_token: string | null
  constructor(div_selector: string, cmk_token: string | undefined | null = null) {
    super(div_selector)
    this._cmk_token = typeof cmk_token !== 'undefined' ? cmk_token : null
  }

  override _get_tab_entries() {
    return [EngagedAlertsTab, PastAlertsTab, FlowAlertsTab]
  }

  //TODO: this method is overwritten in the subclasses of TabsBar but doesn't
  // always have a matching signature which leads to a TS2416 error so it might
  // be necessary to create a consistent signature or find another solution
  // @ts-ignore
  initialize(ifid: string) {
    TabsBar.prototype.initialize.call(this)
    this._activate_tab(this.get_tab_by_id('engaged_alerts_tab'))
    selectAll<any, ABCAlertsPage>('.' + ifid_dep)
      .data()
      .forEach((o) => o.set_ids(ifid))
  }

  _show_error_info(error_info: string) {
    console.log('data fetch error ' + error_info)
  }

  get_tabs_list() {
    return this._tabs_list
  }
}

type ABCAlertsFilteredChoices = FlowDashletDataChoice
type ABCAlertsTimeSeries = [string, number][]

interface ABCAlertsPageData extends FigureData {
  ntop_link: string
  alerts: Alert[]
  filter_choices: ABCAlertsFilteredChoices[]
  time_series: ABCAlertsTimeSeries
  number_of_alerts: number
}

interface CrossfilterRecord {
  date: Date
  count: number
}

// Base class for all alert tables
abstract class ABCAlertsPage extends FigureBase<ABCAlertsPageData> {
  _filter_choices: ABCAlertsFilteredChoices[]
  _ifid!: string | null
  _vlanid!: string | null
  _fetch_filters!: Record<string, string>
  current_ntophost: any
  url_param!: string
  _multi_data_fetcher: MultiDataFetcher
  _table_div!: Selection<HTMLDivElement, any, BaseType, any>
  _pagination!: Selection<HTMLDivElement, any, BaseType, any>
  _indexDim!: Dimension<any, any>
  _msgDim!: Dimension<any, any>
  _crossfilterTime!: crossfilter.Crossfilter<CrossfilterRecord>
  _dateDimension!: crossfilter.Dimension<CrossfilterRecord, Date>
  _hourDimension!: crossfilter.Dimension<CrossfilterRecord, number>
  _dateGroup!: crossfilter.Group<CrossfilterRecord, Date, number>
  _hourGroup!: crossfilter.Group<CrossfilterRecord, number, number>
  _filteredDate: null | any[] = null
  _filteredHours: null | any[] = null
  _scaleDate_x!: d3.ScaleTime<Date, number>
  _scaleDate_y!: d3.ScaleLinear<number, number>
  _scaleHour_x!: d3.ScaleLinear<number, number>
  _scaleHour_y!: d3.ScaleLinear<number, number>

  _dateFilterContext!: Selection<SVGGElement, unknown, BaseType, unknown>
  _hourFilterContext!: Selection<SVGGElement, unknown, BaseType, unknown>
  constructor(div_selector: string) {
    super(div_selector)
    this._filter_choices = []
    this._multi_data_fetcher = new MultiDataFetcher()
    this._indexDim = this._crossfilter.dimension((d) => d.index)
    this._msgDim = this._crossfilter.dimension((d) => d.msg)
    this._crossfilterTime = crossfilter()
    this._dateDimension = this._crossfilterTime.dimension<Date>((d) => d.date)
    this._hourDimension = this._crossfilterTime.dimension<number>((d) => {
      return d.date.getHours() + d.date.getMinutes() / 60
    })
    this._dateGroup = this._dateDimension
      .group<Date, number>((d) => {
        return d3.timeDay.floor(d)
      })
      .reduceSum((d) => d.count)
    this._hourGroup = this._hourDimension
      .group<number, number>((d) => {
        return Math.floor(d)
      })
      .reduceSum((d) => d.count)
  }

  _update_details_table() {
    const parameters = this.get_url_search_parameters()
    parameters.append('details_only', '1')
    parameters.append('offset', this._pagination.select('td.pagination_info').attr('offset'))

    this._multi_data_fetcher.reset()
    this._multi_data_fetcher.add_fetch_operation(this._post_url, parameters.toString(), 600)
    this._multi_data_fetcher.subscribe_hook(this._post_url, parameters.toString(), (data) =>
      this._update_details_data(data)
    )
    this.show_loading_image()
  }

  _update_details_data(data: ABCAlertsPageData) {
    if (data === undefined) return
    this._crossfilter.remove(() => true)
    data.alerts.forEach(function (d, i) {
      d.index = i
      // @ts-ignore
      d.date = new Date(1000 * d.date)
    })
    this._crossfilter.add(data.alerts)
    this._render_table()
  }

  override initialize(_with_debugging?: boolean) {
    // Date and hour filters
    this._initialize_time_filters(
      this._div_selection.append('div').classed('time_filters ' + this.page_id(), true)
    )

    this._initialize_fetch_filters(
      this._div_selection.append('div').classed('fetch_filters ' + this.page_id(), true)
    )

    this._initialize_description_filter(
      this._div_selection.append('div').classed('description_filter ' + this.page_id(), true)
    )

    this._div_selection
      .append('div')
      .classed('warning ' + this.page_id(), true)
      .style('display', 'none')
      .html(
        '<b>Note: </b> When using both day and hour filters, only the selected hours of the last day will be evaluated.'
      )
    this._div_selection.append('div').classed('details ' + this.page_id(), true)

    // Parameters used for url generation
    this._ifid = null
    this._vlanid = null
    this._fetch_filters = {}

    this._div_selection = this._div_selection.classed(ifid_dep, true)
    this._div_selection.datum(this)

    this._multi_data_fetcher.scheduler.enable()
    // Table
    this._pagination = this._div_selection.append('div').attr('id', 'table_pagination')
    this._table_div = this._div_selection.append('div').attr('id', 'details_table')
    this._render_table_pagination()
  }

  getEmptyData() {
    return {
      data: [],
      plot_definitions: [],
      ntop_link: '',
      alerts: [],
      filter_choices: [],
      time_series: [],
      number_of_alerts: 0
    }
  }

  page_id() {
    return ''
  }

  update_post_body() {
    const parameters = this.get_url_search_parameters()
    // The post body of this function is always only responsible for the timeseries graphs
    parameters.append('timeseries_only', '1')
    this._post_body = parameters.toString()
  }

  get_url_search_parameters() {
    const parameters = new URLSearchParams()
    const params = Object.assign(
      { ifid: this._ifid, vlanid: this._vlanid },
      this._fetch_filters,
      this._get_time_filter_params(),
      this.current_ntophost == undefined ? {} : { host: this.current_ntophost }
    )
    Object.keys(params).forEach((key) => {
      parameters.append(key, params[key])
    })
    return parameters
  }

  set_ids(ifid: string, vlanid = '0') {
    this._ifid = ifid
    this._vlanid = vlanid
    this.update_post_body()
    this.scheduler.force_update()
  }

  _initialize_time_filters(selection: Selection<HTMLDivElement, unknown, BaseType, unknown>) {
    const datetime_filter = selection.append('table').style('margin-top', '20px')
    datetime_filter
      .append('tr')
      .selectAll('td')
      .data(['day', 'hour'])
      .join('td')
      .text((d) => 'Filter by ' + d)
    const filter_row = datetime_filter.append('tr')

    // Day filter
    const now = new Date()
    this._scaleDate_x = d3.scaleTime<Date, number>()
    this._scaleDate_y = d3.scaleLinear<number, number>()
    this._scaleDate_y.range([0, 130])
    this._dateFilterContext = this._initialize_time_filter(
      filter_row.append('td').append('svg'),
      [new Date((now.getTime() / 1000 - 31 * 86400) * 1000), now],
      this._scaleDate_x,
      5,
      (selection: [Date, Date], scale: d3.ScaleTime<any, any>) => {
        let [x0, x1] = scale.domain()
        this._filteredDate = null
        this._dateDimension.filterRange([x0, x1])
        if (selection !== null) {
          ;[x0, x1] = selection.map((d) => scale.invert(d))
          this._filteredDate = [x0, x1]
          this._dateDimension.filterRange([x0, x1])
        }
        this._update_time_filters()
        this._update_details_table()
      }
    )

    // Hours filter
    this._scaleHour_x = d3.scaleLinear<number, number>()
    this._scaleHour_y = d3.scaleLinear<number, number>()
    this._scaleHour_y.range([0, 130])
    this._hourFilterContext = this._initialize_time_filter(
      filter_row.append('td').append('svg'),
      [0, 24],
      this._scaleHour_x,
      12,
      (selection: [number, number], scale: d3.ScaleLinear<number, number>) => {
        let [x0, x1] = scale.domain()
        this._filteredHours = null
        this._hourDimension.filterRange([x0, x1])
        if (selection !== null) {
          ;[x0, x1] = selection.map((d) => scale.invert(d))
          this._filteredHours = [x0, x1]
          this._hourDimension.filterRange([x0, x1])
        }
        this._update_time_filters()
        this._update_details_table()
      }
    )
  }

  _initialize_time_filter(
    svg: Selection<SVGSVGElement, unknown, BaseType, unknown>,
    use_domain: [number, number] | [Date, Date],
    use_scale: d3.ScaleTime<Date, number> | d3.ScaleLinear<number, number>,
    ticks: number,
    changed_callback: any = null
  ) {
    const margin = { top: 20, right: 30, bottom: 50, left: 40 }
    svg.attr('height', 200).attr('width', 500)
    const width = +svg.attr('width') - margin.left - margin.right
    const height = +svg.attr('height') - margin.top - margin.bottom
    const x_time = use_scale.range([0, width])

    // @ts-ignore
    const fixedAxis = d3.axisBottom(use_scale).ticks(ticks)
    const brush = d3
      .brushX()
      .extent([
        [0, 0],
        [width, height]
      ])
      .on('end', (event: D3BrushEvent<any>) => {
        changed_callback(event.selection, use_scale)
      })

    const context = svg
      .append('g')
      .attr('class', 'context')
      .attr('transform', `translate(${margin.left},${margin.top})`)

    // @ts-ignore
    x_time.domain(use_domain)

    context
      .append('g')
      .attr('class', 'x axis')
      .attr('transform', `translate(0,${height})`)
      .call(fixedAxis)

    context.append('g').attr('class', 'brush').call(brush)
    return context
  }

  _update_time_filters() {
    // Update date
    let max_y_date = d3.max(this._dateGroup.all(), (d) => d.value)!
    max_y_date = Math.max(max_y_date, 1)
    this._scaleDate_y.domain([max_y_date, 0])
    this._dateFilterContext
      .selectAll('g.axis_left')
      .data([null])
      .join('g')
      .classed('axis_left', true)
      .transition()
      // @ts-ignore
      .call(d3.axisLeft(this._scaleDate_y).ticks(4))

    this._dateFilterContext
      .selectAll<SVGRectElement, { key: number; value: number }>('rect.data')
      .data(this._dateGroup.all())
      .join('rect')
      .classed('data', true)
      .style('pointer-events', 'none')
      .style('fill', 'lightblue')
      .attr('width', 10)
      .attr('x', (d: { key: Date; value: number }): number => {
        return this._scaleDate_x(d.key)
      })
      .transition()
      .attr('y', (d) => this._scaleDate_y(0) - this._scaleDate_y(max_y_date - d.value))
      .attr('height', (d) => {
        return this._scaleDate_y(max_y_date - d.value)
      })

    // Update hours
    let max_y_hour = d3.max(this._hourGroup.all(), (d) => d.value)!
    max_y_hour = Math.max(max_y_hour, 1)
    this._scaleHour_y.domain([max_y_hour, 0])
    this._hourFilterContext
      .selectAll('g.axis_left')
      .data([null])
      .join('g')
      .classed('axis_left', true)
      .transition()
      // @ts-ignore
      .call(d3.axisLeft(this._scaleHour_y).ticks(4))

    this._hourFilterContext
      .selectAll<SVGRectElement, { key: number; value: number }>('rect.data')
      .data(this._hourGroup.all())
      .join('rect')
      .classed('data', true)
      .style('pointer-events', 'none')
      .style('fill', 'lightblue')
      .attr('width', 10)
      .attr('x', (d) => {
        return this._scaleHour_x(d.key)
      })
      .transition()
      .attr('height', (d) => {
        return this._scaleHour_y(max_y_hour - d.value)
      })
      .attr('y', (d) => this._scaleHour_y(0) - this._scaleHour_y(max_y_hour - d.value))
  }

  _update_filter_choices(filter_choices: FlowDashletDataChoice[]) {
    this._filter_choices = filter_choices
    this._initialize_fetch_filters(
      this._div_selection.select('div.fetch_filters.' + this.page_id())
    )
  }

  _initialize_fetch_filters(selection: Selection<HTMLDivElement, unknown, BaseType, unknown>) {
    const dropdowns = selection
      .selectAll('div.dropdown')
      .data(this._filter_choices)
      .join('div')
      .style('display', 'inline-block')
      .classed('dropdown', true)
    dropdowns
      .selectAll('label')
      .data((d) => [d])
      .join('label')
      .text((d) => d.group)
    const select = dropdowns
      .selectAll('select')
      .data((d) => [d])
      .join('select')
      .attr('class', 'filter alerts select2-enable')

    select
      .selectAll('option')
      .data((d) => d.choices)
      .join((enter) =>
        enter
          .append('option')
          .property('value', (d) => '' + d.id)
          .text((d) => d.name)
      )

    const elements = $('div.dropdown').find('.select2-enable')
    const select2 = elements.select2({
      dropdownAutoWidth: true,
      minimumResultsForSearch: 5
    })
    select2.on('select2:select', (event) => {
      this._fetch_filters_changed(event)
    })
  }

  _fetch_filters_changed(event: Event) {
    if (event.target == null) return
    const selectTarget = event.target as HTMLSelectElement
    const target = select<HTMLSelectElement, ABCAlertsPage>(selectTarget)
    this._fetch_filters = {}
    //@ts-ignore
    if (selectTarget.value != -1) this._fetch_filters[target.datum().url_param] = selectTarget.value
    this.update_post_body()

    // Reset all other filters
    const selected_index = selectTarget.selectedIndex
    this._div_selection.selectAll('select.filter.alerts option').property('selected', false)
    selectTarget.selectedIndex = selected_index
    this.show_loading_image()
    this.scheduler.force_update()
  }

  _render_table_pagination() {
    const entries = 20

    const new_row = this._pagination
      .selectAll('table')
      .data([null])
      .enter()
      .append('table')
      .style('width', '260px')
      .style('margin', '10px')
      .style('margin-left', 'auto')
      .style('margin-right', '0px')
      .append('tr')
    const current_pagination = new_row
      .append('td')
      .classed('pagination_info', true)
      .style('width', '160px')
      .style('text-align', 'right')
      .attr('offset', 0)
    ;[
      ['<<', 0],
      ['<', -entries],
      ['>', entries],
      ['>>', Infinity]
    ].forEach((entry) => {
      const [text, offset] = entry
      new_row
        .append('td')
        .classed('navigation noselect', true)
        .style('cursor', 'pointer')
        .on('mouseover', (event: MouseEvent) => {
          d3.select(event.target! as HTMLElement).style('background', '#9c9c9c')
        })
        .on('mouseout', (event: MouseEvent) => {
          d3select(event.target! as HTMLElement).style('background', null)
        })
        .text(text)
        .attr('offset', offset)
        .on('click', (event: MouseEvent) => {
          const old_offset = parseInt(current_pagination.attr('offset'))
          const delta = d3select(event.target! as HTMLElement).attr('offset')
          var from = 0

          const total_entries = this._data.number_of_alerts

          if (delta == 'Infinity') {
            from = Math.floor(total_entries / entries) * entries
          } else {
            const num_delta = parseInt(delta)
            if (num_delta == 0) {
              from = 0
            } else {
              from = old_offset + num_delta
              if (from < 0) from = 0
              if (from > total_entries) from = old_offset
            }
          }

          current_pagination.attr('offset', from)
          this._update_pagination_text()
          this._update_details_table()
        })
    })
    this._update_pagination_text()
  }

  _update_pagination_text() {
    const offset = parseInt(this._pagination.select('td.pagination_info').attr('offset'))
    const total_entries = this._data.number_of_alerts
    const to = Math.min(offset + 20, total_entries)
    this._pagination.select('td.pagination_info').text(`${offset} - ${to} of ${total_entries}`)
  }

  _render_table() {
    const columns = this._get_columns()
    this.remove_loading_image()
    this._render_table_pagination()
    const table = this._table_div
      .selectAll('table')
      .data([this._crossfilter.allFiltered()])
      .join('table')

    // Headers, only once
    table
      .selectAll('thead')
      .data([columns])
      .enter()
      .append('thead')
      .append('tr')
      .selectAll('th')
      .data((d) => d)
      .join('th')
      .text((d) => d.label)

    // Rows
    const rows = table
      .selectAll('tbody')
      .data((d) => [d])
      .join('tbody')
      .selectAll('tr')
      .data((d) => d)
      .join('tr')
      .attr('class', 'table_row')

    columns.forEach((entry) => {
      const cell = rows
        .selectAll<HTMLTableCellElement, FlowData>(`td.${entry.label.replace(' ', '_')}`)
        .data((d) => [d])
        .join('td')
        .classed(entry.label.replace(' ', '_'), true)
      cell.html((d) => entry.format(d))
      cell.classed(entry.classes.join(' '), true)
    })

    add_classes_to_trs(this._table_div)
    this._update_severity(this._table_div)
  }

  _compute_status_text(filter_params: Record<string, number>) {
    function _format_date(timestamp: number, skip_date = false, skip_hours = false) {
      const date = new Date(timestamp * 1000)
      let response = ''
      if (!skip_date)
        response +=
          date.getFullYear() + '/' + (date.getMonth() + 1) + '/' + (date.getDate() + 1) + ' '
      if (!skip_hours) {
        response += ('0' + date.getHours()).slice(-2) + ':' + ('0' + date.getMinutes()).slice(-2)
      }
      return response
    }
    function _format_absolute_hour(hour_number: number) {
      const timezoneOffset = new Date().getTimezoneOffset()
      hour_number = Math.trunc(hour_number) * 60 - timezoneOffset
      return (
        ('00' + Math.floor(hour_number / 60)).slice(-2) +
        ':' +
        ('00' + (hour_number % 60)).slice(-2)
      )
    }

    let status_text = 'Alert details'
    if (filter_params.date_start != undefined && filter_params.hour_start == undefined) {
      status_text +=
        ' from ' +
        _format_date(filter_params.date_start) +
        ' to ' +
        _format_date(filter_params.date_end)
    } else if (filter_params.hour_start != undefined) {
      const day_string =
        filter_params.date_end != undefined
          ? ' on ' + _format_date(filter_params.date_end, false, true)
          : ' today'
      status_text +=
        ' from ' +
        _format_absolute_hour(filter_params.hour_start) +
        ' to ' +
        _format_absolute_hour(filter_params.hour_end) +
        day_string
    } else status_text += ' from last 31 days'

    return status_text
  }

  _get_time_filter_params() {
    const filter_params: Record<string, number> = {}
    const hour_filter = this._filteredHours
    const timezoneOffset = new Date().getTimezoneOffset() / 60
    if (hour_filter) {
      filter_params['hour_start'] = hour_filter[0] + timezoneOffset
      filter_params['hour_end'] = hour_filter[1] + timezoneOffset
    }

    const date_filter = this._filteredDate!

    if (date_filter) {
      filter_params['date_start'] = Math.trunc(date_filter[0].getTime() / 1000)
      filter_params['date_end'] = Math.trunc(date_filter[1].getTime() / 1000)
    }
    return filter_params
  }

  _initialize_description_filter(selection: Selection<HTMLDivElement, unknown, BaseType, unknown>) {
    selection.append('label').text('Filter details by description')
    selection
      .append('input')
      .attr('type', 'text')
      .classed('msg_filter', true)
      .on('input', (event: Event) => {
        const target = select(event.target as HTMLInputElement)
        const filter = target.property('value')
        this._msgDim.filter((d) => {
          //@ts-ignore
          return d.toLowerCase().includes(filter.toLowerCase())
        })
        this._render_table()
      })
  }

  _setup_status_text(selection: Selection<HTMLDivElement, unknown, BaseType, unknown>) {
    selection.classed('status', true).append('label')
  }

  _update_severity(selection: Selection<HTMLDivElement, unknown, BaseType, unknown>) {
    add_columns_classes_to_nodes(selection, this._get_columns())

    const state_mapping = new Map<string, string>([
      ['error', 'state2'],
      ['emergency', 'state2'],
      ['critical', 'state2'],
      ['warning', 'state1'],
      ['notice', 'state0'],
      ['debug', 'state0'],
      ['info', 'state0'],
      ['none', 'state3']
    ])
    // Add state class to severity
    selection.selectAll<HTMLTableCellElement, Alert>('td.severity').each((d, idx, nodes) => {
      const label = select(nodes[idx]).select('label')
      label.classed('badge', true)
      const state = state_mapping.get(d.severity.toLowerCase())
      if (state) label.classed(state, true)
    })
  }

  override update_data(data: ABCAlertsPageData) {
    FigureBase.prototype.update_data.call(this, data)
    const time: CrossfilterRecord[] = []
    data.time_series.forEach((entry) => {
      time.push({
        //@ts-ignore
        date: new Date(entry[0] * 1000),
        count: entry[1]
      })
    })

    this._crossfilterTime.remove(() => true)
    this._crossfilterTime.add(time)
    this._update_filter_choices(data.filter_choices)
    this._update_pagination_text()
    this._update_details_table()
    this._update_time_filters()
  }

  override update_gui() {}

  abstract _get_columns(): NtopColumn[]

  get_multi_data_fetcher() {
    return this._multi_data_fetcher
  }
}

// Base class for all alert tabs
export abstract class ABCAlertsTab<Page extends ABCAlertsPage = ABCAlertsPage> extends Tab {
  _page_class: null | (new (div_selector: string, cmk_token?: string | null) => Page)
  _alerts_page!: Page
  _cmk_token: string | null
  constructor(tabs_bar: TabsBar, cmk_token: string | null = null) {
    super(tabs_bar)
    this._page_class = null
    this._tab_selection.classed('ntop_alerts', true)
    this._cmk_token = cmk_token
  }

  initialize() {
    const div_id = this.tab_id() + '_alerts_table'
    this._tab_selection.append('div').attr('id', div_id)
    if (this._page_class) {
      this._alerts_page = new this._page_class('#' + div_id, this._cmk_token)
      this._alerts_page.initialize()
    }
  }

  // eslint-disable-next-line @typescript-eslint/no-empty-function
  activate() {}

  // eslint-disable-next-line @typescript-eslint/no-empty-function
  deactivate() {}

  get_page() {
    return this._alerts_page
  }
}

//   .-Engaged------------------------------------------------------------.
//   |              _____                                  _              |
//   |             | ____|_ __   __ _  __ _  __ _  ___  __| |             |
//   |             |  _| | '_ \ / _` |/ _` |/ _` |/ _ \/ _` |             |
//   |             | |___| | | | (_| | (_| | (_| |  __/ (_| |             |
//   |             |_____|_| |_|\__, |\__,_|\__, |\___|\__,_|             |
//   |                          |___/       |___/                         |
//   +--------------------------------------------------------------------+
export class EngagedAlertsTab extends ABCAlertsTab<EngagedAlertsPage> {
  constructor(tabs_bar: TabsBar, cmk_token: string | null = null) {
    super(tabs_bar, cmk_token)
    this._page_class = EngagedAlertsPage
  }

  tab_id() {
    return 'engaged_alerts_tab'
  }

  name() {
    return 'Engaged Host'
  }
}

//cmk.gui.cee.ntop.connector.NtopAPIv2._build_alert_msg
export interface Alert {
  index: number //created in JS
  entity: string
  duration: number
  count: number
  msg: string
  date: string
  entity_val: string
  drilldown: null // Not used
  type: string
  severity: string
  score: string
  needs_id_transform: boolean
}

class EngagedAlertsPage extends ABCAlertsPage {
  constructor(div_selector: string, cmk_token: string | null = null) {
    super(div_selector)
    if (cmk_token !== null) {
      const http_var_string: string = new URLSearchParams({ 'cmk-token': cmk_token }).toString()
      this._post_url = `ntop_engaged_alerts_token_auth.py?${http_var_string}`
    } else {
      this._post_url = 'ajax_ntop_engaged_alerts.py'
    }
  }

  override page_id() {
    return 'engaged_alerts'
  }

  override initialize(with_debugging?: boolean) {
    super.initialize(with_debugging)
    this.subscribe_data_pre_processor_hook((data) => {
      const days: Record<string, number> = {}
      const timeseries_data: [number, number][] = []
      data.alerts.forEach((alert: Alert) => {
        if (this._filter_entity(alert.entity_val)) return
        const start_timestamp = alert.date
        days[start_timestamp] = (days[start_timestamp] || 0) + 1
      })
      for (const start_timestamp in days) {
        timeseries_data.push([parseInt(start_timestamp), days[start_timestamp]])
      }
      return {
        time_series: timeseries_data,
        filter_choices: data.filter_choices,
        ntop_link: data.ntop_link,
        number_of_alerts: data.number_of_alerts
      }
    })
  }

  _filter_entity(_entity_val: string) {
    return false
  }

  _get_columns() {
    return [
      {
        label: 'Date',
        format: (d: Alert) => {
          return (
            //@ts-ignore
            d.date.toLocaleDateString('de') +
            ' ' +
            //@ts-ignore
            d.date.toLocaleTimeString('de')
          )
        },
        classes: ['date', 'number']
      },
      {
        label: 'Duration',
        format: (d: Alert) => {
          return seconds_to_time(d.duration)
        },
        classes: ['duration', 'number']
      },
      {
        label: 'Severity',
        format: (d: Alert) => {
          return '<label>' + d.severity + '</label>'
        },
        classes: ['severity']
      },
      {
        label: 'Alert type',
        format: (d: Alert) => d.type,
        classes: ['alert_type']
      },
      {
        label: 'Description',
        format: (d: Alert) => d.msg,
        classes: ['description']
      }
    ]
  }
}

//   .-Past---------------------------------------------------------------.
//   |                         ____           _                           |
//   |                        |  _ \ __ _ ___| |_                         |
//   |                        | |_) / _` / __| __|                        |
//   |                        |  __/ (_| \__ \ |_                         |
//   |                        |_|   \__,_|___/\__|                        |
//   |                                                                    |
//   +--------------------------------------------------------------------+
export class PastAlertsTab extends ABCAlertsTab {
  constructor(tabs_bar: TabsBar, cmk_token: string | null = null) {
    super(tabs_bar, cmk_token)
    this._page_class = PastAlertsPage
  }

  tab_id() {
    return 'past_alerts_tab'
  }

  name() {
    return 'Past Host'
  }
}

class PastAlertsPage extends ABCAlertsPage {
  constructor(div_selector: string, cmk_token: string | null = null) {
    super(div_selector)
    if (cmk_token !== null) {
      const http_var_string: string = new URLSearchParams({ 'cmk-token': cmk_token }).toString()
      this._post_url = `ntop_past_alerts_token_auth.py?${http_var_string}`
    } else {
      this._post_url = 'ajax_ntop_past_alerts.py'
    }
  }

  override page_id() {
    return 'past_alerts'
  }

  _get_columns() {
    return [
      {
        label: 'Date',
        format: (d: Alert) => {
          return (
            //@ts-ignore
            d.date.toLocaleDateString('de') +
            ' ' +
            //@ts-ignore
            d.date.toLocaleTimeString('de')
          )
        },
        classes: ['date', 'number']
      },
      {
        label: 'Duration',
        format: (d: Alert) => {
          return seconds_to_time(d.duration)
        },
        classes: ['duration', 'number']
      },
      {
        label: 'Severity',
        format: (d: Alert) => {
          return '<label>' + d.severity + '</label>'
        },
        classes: ['severity']
      },
      {
        label: 'Alert type',
        format: (d: Alert) => d.type,
        classes: ['alert_type']
      },
      {
        label: 'Description',
        format: (d: Alert) => d.msg,
        classes: ['description']
      }
    ]
  }
}

//   .-Flows--------------------------------------------------------------.
//   |                      _____ _                                       |
//   |                     |  ___| | _____      _____                     |
//   |                     | |_  | |/ _ \ \ /\ / / __|                    |
//   |                     |  _| | | (_) \ V  V /\__ \                    |
//   |                     |_|   |_|\___/ \_/\_/ |___/                    |
//   |                                                                    |
//   +--------------------------------------------------------------------+

export class FlowAlertsTab extends ABCAlertsTab {
  constructor(tabs_bar: TabsBar, cmk_token: string | null = null) {
    super(tabs_bar, cmk_token)
    this._page_class = FlowAlertsPage
  }

  tab_id() {
    return 'flow_alerts_tab'
  }

  name() {
    return 'Past Flow'
  }
}

class FlowAlertsPage extends ABCAlertsPage {
  constructor(div_selector: string, cmk_token: string | null = null) {
    super(div_selector)
    if (cmk_token !== null) {
      const http_var_string: string = new URLSearchParams({ 'cmk-token': cmk_token }).toString()
      this._post_url = `ntop_flow_alerts_token_auth.py?${http_var_string}`
    } else {
      this._post_url = 'ajax_ntop_flow_alerts.py'
    }
  }

  override page_id() {
    return 'flow_alerts'
  }

  _get_columns() {
    return [
      {
        label: 'Date',
        format: (d: Alert) => {
          return (
            //@ts-ignore
            d.date.toLocaleDateString('de') +
            ' ' +
            //@ts-ignore
            d.date.toLocaleTimeString('de')
          )
        },
        classes: ['date', 'number']
      },
      {
        label: 'Severity',
        format: (d: Alert) => {
          return '<label>' + d.severity + '</label>'
        },
        classes: ['severity']
      },
      {
        label: 'Alert type',
        format: (d: Alert) => d.type,
        classes: ['alert_type']
      },
      {
        label: 'Score',
        format: (d: Alert) => d.score,
        classes: ['score', 'number']
      },
      {
        label: 'Description',
        format: (d: Alert) => d.msg,
        classes: ['description']
      }
    ]
  }
}
