/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/* eslint  @typescript-eslint/no-unused-vars: 0, @typescript-eslint/no-empty-interface: 0 */
//TODO: this is kind of code duplication, since the types are defined twice
// in python and typescript, so maybe in the future it would be better to have
// a way to automatically generate them from one sie to another

export interface SubplotDataData {
  x?: [Date | undefined, Date | undefined]
  y?: [number, number | undefined]
  data: TransformedData[]
}

//types from: cmk/gui/cee/plugins/dashboard/site_overview.py
export interface ABCElement {
  type: string
  title: string
  tooltip: string
}

export interface SiteElement extends ABCElement {
  type: 'site_element'
  url_add_vars: Record<string, string>
  total: Part
  parts: Part[]
}

export interface HostElement extends ABCElement {
  hexagon_config: {
    css_class: string
    path: string
    color?: number
    tooltip: string
    id: string
  }[]
  x: number
  y: number
  type: 'host_element'
  link: string
  host_css_class: string
  service_css_class: string
  has_host_problem: boolean
  num_services: number
  num_problems: number
}

export interface IconElement extends ABCElement {
  type: 'icon_element'
  css_class: string
}

export interface Part {
  title: string
  css_class: string
  count: number
}

export interface SingleMetricDataData {
  tag: string
  last_value: boolean
  timestamp: number
  value: number
  label: any
  url: string
}

export interface SingleMetricDataPlotDefinitions {
  label: any
  id: string
  plot_type: string
  style: string
  status_display: Record<string, string>
  use_tags: string[]
  color: string
  opacity: number
  metric: Record<string, Record<string, any>>
}

export interface ElementMargin {
  top: number
  right: number
  bottom: number
  left: number
}

export interface FigureData<D = any, P = any> {
  //TODO: in all figureBase subclasses data is an array of data or it's not used at all like
  // in case of ntop figures, however, it's in some cases only on element (as type not a single element array)
  // like in HostStateSummary and ServiceStateSummary. This causes typing confusion and possible errors
  // so it might be better to change the structure of the above mentioned classes.
  data: D[] | D
  plot_definitions: P[]
}

export interface SingleMetricData
  extends FigureData<SingleMetricDataData, SingleMetricDataPlotDefinitions> {
  data: SingleMetricDataData[]
  title: string
  title_url: string
}

export interface ElementSize {
  width: number
  height: number
}

export type Levels = {
  from: number
  to: number
  style: string
}

interface _Metric {
  bounds: Bounds
  unit: any
}

export interface Bounds {
  warn?: number
  crit?: number
  min?: number
  max?: number
}

export type Domain = [number, number]

export interface TransformedData {
  label: any
  scaled_y: number
  scaled_x: number
  value: number
  unstacked_value: number
  timestamp: number
  date: Date
  ending_timestamp?: number
  url?: string
  last_value?: number
  tooltip?: string
}

/* We cannot easily import from cmk-shared-typing here, which is where the Vue dashboard code gets
 * the API spec content types from. So the following type declarations duplicate only what's needed
 * in the figures/ code (call sites of _widget_content) and do not reflect the whole of the API
 * models.
 * If other properties of FigureBase._widget_content need to be accessed, the respective types need
 * to be updated here as well.
 * This general type FigureWidgetContent accepts optional unknown properties not to duplicate all
 * figure widget content types from the API models. */
type _UnknownContentProps = Record<string, unknown>
export interface FigureWidgetContent extends _UnknownContentProps {
  type: string
}

type MetricDisplayRangeFixedModel = {
  type: 'fixed'
  unit: string
  minimum: number
  maximum: number
}
type MetricDisplayRangeModel = 'automatic' | MetricDisplayRangeFixedModel

// Specific figure content types
export interface BarplotContent extends FigureWidgetContent {
  type: 'barplot'
  display_range: MetricDisplayRangeModel
}
export interface GaugeContent extends FigureWidgetContent {
  type: 'gauge'
  display_range: MetricDisplayRangeFixedModel
}
export interface SingleMetricContent extends FigureWidgetContent {
  type: 'single_metric'
  display_range: MetricDisplayRangeModel
  show_display_range_limits: boolean
}
