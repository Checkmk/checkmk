/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Dimension } from 'crossfilter2'
import type { AxisDomain, BaseType, ScaleLinear, Selection } from 'd3'
import { axisLeft, axisRight, axisTop, max, range, scaleLinear } from 'd3'

import { FigureTooltip } from '@/modules/figures/cmk_figure_tooltip'
import { FigureBase } from '@/modules/figures/cmk_figures'
import { add_scheduler_debugging, getIn } from '@/modules/figures/cmk_figures_utils'
import { Domain, FigureData, SingleMetricDataPlotDefinitions } from '@/modules/figures/figure_types'
import { domainIntervals, partitionableDomain } from '@/modules/number_format'

export interface BarplotData {
  ident: string
  value: number
  tag: string
  label: string
  tooltip: string
  url: string
}

export interface BarplotFigureData extends FigureData<BarplotData> {
  title: string
  title_url: string
}

export class HorizontalBarFigure extends FigureBase<BarplotFigureData> {
  _tag_dimension: Dimension<any, string>
  _plot_definitions: SingleMetricDataPlotDefinitions[]
  bars!: Selection<SVGGElement, unknown, any, any>
  scale_x!: ScaleLinear<number, number, never>
  tooltip_generator!: FigureTooltip

  override ident() {
    return 'horizontal_barplot'
  }

  constructor(div_selector: string, fixed_size = null) {
    super(div_selector, fixed_size)
    this.margin = { top: 20, right: 10, bottom: 10, left: 10 }

    this._tag_dimension = this._crossfilter.dimension((d) => d.tag)
    this._plot_definitions = []
  }

  override initialize() {
    this.svg = this._div_selection.append('svg').classed('renderer', true)
    this.plot = this.svg.append('g')
    this.bars = this.plot.append('g').classed('barplot', true)

    // X axis
    this.scale_x = scaleLinear()
    this.plot.append('g').classed('x_axis', true).call(axisTop(this.scale_x))

    this.tooltip_generator = new FigureTooltip(this._div_selection.append('div'))
  }

  getEmptyData() {
    return { data: [], plot_definitions: [], title: '', title_url: '' }
  }

  override render() {
    if (this._data) this.update_gui()
  }

  override resize() {
    if (this._data.title) {
      this.margin.top = 20 + 24 // 24 from UX project
    } else {
      this.margin.top = 20
    }
    FigureBase.prototype.resize.call(this)
    this.svg!.attr('width', this.figure_size.width).attr('height', this.figure_size.height)
    this.scale_x.range([0, this.plot_size.width])
    this.plot.attr('transform', 'translate(' + this.margin.left + ',' + this.margin.top + ')')
  }

  _update_plot_definitions(plot_definitions: SingleMetricDataPlotDefinitions[]) {
    this._plot_definitions = []

    // We are only interested in the single_value plot types, they may include metrics info
    plot_definitions.forEach((plot_definition) => {
      if (plot_definition.plot_type != 'single_value') return
      this._plot_definitions.push(plot_definition)
    })
  }

  render_grid(ticks: number[]) {
    // Grid
    const height = this.plot_size.height
    this.plot
      .selectAll<SVGElement, null>('g.grid.vertical')
      .data([null])
      .join('g')
      .classed('grid vertical', true)
      .call(
        // @ts-ignore
        axisTop(this.scale_x)
          .tickValues(ticks)
          .tickSize(-height)
          .tickFormat((_x, _y) => '')
      )
  }

  override update_gui() {
    const data = this._data
    this._update_plot_definitions(data.plot_definitions || [])
    if (data.plot_definitions.length == 0) return
    this._crossfilter.remove(() => true)
    this._crossfilter.add(data.data as BarplotData[])

    this.resize()
    this.render_title(data.title, data.title_url!)

    this.tooltip_generator.update_sizes(this.figure_size, this.plot_size)

    this.render_axis()
    this._render_values()
  }

  render_axis(): Domain {
    const value_labels = this._plot_definitions.map((d) => d.label)
    this.scale_x.domain(value_labels)
    const axis_labels = axisLeft(this.scale_x)
    // 12 is UX font-height, omit labels when not enough space
    if (value_labels.length >= this.plot_size.height / 12) axis_labels.tickFormat((_x, _y) => '')

    this.plot
      .selectAll('g.y_axis')
      .classed('axis', true)
      // @ts-ignore
      .call(axis_labels)
      .selectAll('text')
      .attr('transform', `translate(0,50);`)

    const used_tags = this._plot_definitions.map((d) => d.use_tags[0])
    const points = this._tag_dimension.filter((d) => used_tags.includes(String(d))).top(Infinity)

    const tickcount = Math.max(2, Math.ceil(this.plot_size.width / 85))
    // @ts-ignore
    let x_domain: [number, number] = [0, max(points, (d) => d.value)]

    const [min_val, max_val, step] = partitionableDomain(
      x_domain,
      tickcount,
      domainIntervals(getIn(this._plot_definitions[0], 'metric', 'unit', 'stepping'))
    )

    const domain: Domain = [min_val, max_val]
    const tick_vals = range(min_val, max_val, step)

    this.scale_x.domain(domain)
    this._tag_dimension.filterAll()

    const render_function = this.get_scale_render_function()

    this.plot
      .selectAll('g.x_axis')
      .classed('axis', true)
      .style('text-anchor', 'start')
      .call(
        // @ts-ignore
        axisTop(this.scale_x)
          .tickValues(tick_vals)
          .tickFormat((d) => render_function(d).replace(/\.0+\b/, ''))
      )
    this.render_grid(range(min_val, max_val, step / 2))
    return domain
  }

  _render_values() {
    if (!Array.isArray(this._data.data)) return

    const element_height = this.plot_size.height / this._data.data.length - 10
    interface DataAndIndex {
      data: BarplotData
      index: number
    }

    // Rectangles
    const bar_groups = this.bars
      .selectAll<SVGGElement, BarplotData>('g')
      .data(this._data.data, (d) => d.ident)
      .join('g')
      .attr('transform', (_d, idx) => {
        return 'translate(0,' + ((element_height + 10) * idx + 10) + ')'
      })

    bar_groups.each(
      (
        _ignored: BarplotData | SVGGElement,
        idx: number,
        groups: SVGGElement[] | ArrayLike<SVGGElement>
      ) => {
        this.tooltip_generator.add_support(groups[idx])
      }
    )

    const links = bar_groups
      .selectAll<HTMLAnchorElement, BarplotData>('a')
      .data(
        (d) => [d],
        (d) => d.ident
      )
      .join('a')
      .attr('xlink:href', (d) => d.url)

    links
      .selectAll<SVGRectElement, DataAndIndex>('rect.bar')
      .data((d) => [d])
      .join('rect')
      .classed('bar', true)
      .attr('height', element_height)
      .transition()
      .attr('width', (d) => this.scale_x(d.value))
      .attr('rx', 2)

    const text_y_shift = element_height / 2 + 3
    // Texts
    links
      .selectAll<SVGTextElement, BarplotData>('text')
      .data(
        (d) => [d],
        (d) => d.ident
      )
      .join('text')
      .attr('x', 10)
      .attr('y', text_y_shift)
      .text((d) => d.label)

    this._tag_dimension.filterAll()
  }
}
