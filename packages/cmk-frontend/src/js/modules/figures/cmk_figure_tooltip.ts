/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { BaseType, Selection } from 'd3'
import { select } from 'd3'

interface FigureTooltipElementSize {
  width: null | number
  height: null | number
}

// Class which handles the display of a tooltip
// It generates basic tooltips and handles its correct positioning
export class FigureTooltip {
  _tooltip: Selection<HTMLDivElement, unknown, BaseType, unknown>
  figure_size: FigureTooltipElementSize
  plot_size: FigureTooltipElementSize
  _portal: HTMLDivElement | null
  _figure_root: HTMLElement | null
  _global_listeners_active: boolean
  _bound_force_hide = () => this.deactivate()
  _bound_on_document_mousemove = (event: MouseEvent) => {
    if (!this._figure_root) return
    const target = event.target as Node | null
    if (target && !this._figure_root.contains(target)) {
      this.deactivate()
    }
  }

  constructor(tooltip_selection: Selection<HTMLDivElement, unknown, BaseType, unknown>) {
    this._tooltip = tooltip_selection
    this._tooltip
      .style('opacity', 0)
      .style('position', 'absolute')
      .classed('tooltip', true)
      .classed('cmk-figure-tooltip', true)
    this.figure_size = { width: null, height: null }
    this.plot_size = { width: null, height: null }
    this._figure_root = this._resolve_figure_root()
    this._global_listeners_active = false
    this._inherit_figure_classes()
    this._portal = this._ensure_portal()
    this._attach_to_portal()
  }

  update_sizes(figure_size: FigureTooltipElementSize, plot_size: FigureTooltipElementSize) {
    this.figure_size = figure_size
    this.plot_size = plot_size
  }

  update_position(event: MouseEvent) {
    if (!this.active()) return

    const tooltip_size = {
      width: this._tooltip.node()!.offsetWidth,
      height: this._tooltip.node()!.offsetHeight
    }

    const viewport_width = document.documentElement.clientWidth
    const viewport_height = document.documentElement.clientHeight
    const is_at_right_border = event.clientX >= viewport_width - tooltip_size.width
    const is_at_bottom_border = event.clientY >= viewport_height - tooltip_size.height

    const left = is_at_right_border
      ? event.clientX - tooltip_size.width + 'px'
      : event.clientX + 'px'
    const top = is_at_bottom_border
      ? event.clientY - tooltip_size.height + 'px'
      : event.clientY + 'px'
    this._tooltip
      .style('left', left)
      .style('right', 'auto')
      .style('bottom', 'auto')
      .style('top', top)
      .style('pointer-events', 'none')
      .style('opacity', 1)
  }

  add_support(node: SVGGElement) {
    const element = select(node)
    element
      .on('mouseover', (event) => this._mouseover(event))
      .on('mouseleave', (event) => this._mouseleave(event))
      .on('mousemove', (event) => this._mousemove(event))
  }

  activate() {
    this._attach_to_portal()
    this._tooltip.style('display', null)
    this._start_global_listeners()
  }

  deactivate() {
    this._tooltip.style('display', 'none')
    this._stop_global_listeners()
  }

  _ensure_portal(): HTMLDivElement | null {
    const body = document.body
    if (!body) return null
    const existing = body.querySelector('.cmk-figure-tooltip-container')
    if (existing instanceof HTMLDivElement) return existing
    const container = document.createElement('div')
    container.className = 'cmk-figure-tooltip-container'
    body.appendChild(container)
    return container
  }

  _attach_to_portal() {
    const tooltipNode = this._tooltip.node()
    if (!tooltipNode || !this._portal) return
    if (tooltipNode.parentElement !== this._portal) {
      this._portal.appendChild(tooltipNode)
    }
  }

  _resolve_figure_root(): HTMLElement | null {
    const tooltipNode = this._tooltip.node()
    if (!tooltipNode) return null
    return (tooltipNode.closest('.cmk_figure') as HTMLElement) || null
  }

  _inherit_figure_classes() {
    const tooltipNode = this._tooltip.node()
    if (!tooltipNode) return
    const figureNode = this._figure_root
    if (!figureNode) return
    figureNode.classList.forEach((className) => {
      if (className !== 'cmk_figure') {
        tooltipNode.classList.add(className)
      }
    })
  }

  _start_global_listeners() {
    if (this._global_listeners_active) return
    this._global_listeners_active = true
    window.addEventListener('blur', this._bound_force_hide)
    window.addEventListener('scroll', this._bound_force_hide, true)
    window.addEventListener('resize', this._bound_force_hide)
    document.addEventListener('mousemove', this._bound_on_document_mousemove, true)
  }

  _stop_global_listeners() {
    if (!this._global_listeners_active) return
    this._global_listeners_active = false
    window.removeEventListener('blur', this._bound_force_hide)
    window.removeEventListener('scroll', this._bound_force_hide, true)
    window.removeEventListener('resize', this._bound_force_hide)
    document.removeEventListener('mousemove', this._bound_on_document_mousemove, true)
  }

  active() {
    return this._tooltip.style('display') != 'none'
  }

  _mouseover(event: MouseEvent) {
    const node_data = select(event.target as HTMLDivElement).datum()
    // @ts-ignore
    if (node_data == undefined || node_data.tooltip == undefined) {
      this.deactivate()
      return
    }
    this.activate()
  }

  _mousemove(event: MouseEvent) {
    const node_data = select(event.target as HTMLDivElement).datum()
    // @ts-ignore
    if (node_data == undefined || node_data.tooltip == undefined) {
      this.deactivate()
      return
    }
    try {
      // @ts-ignore
      this._tooltip.html(node_data.tooltip)
      this.update_position(event)
    } catch (_error) {
      this.deactivate()
    }
  }

  _mouseleave(_event: MouseEvent) {
    this.deactivate()
  }
}
