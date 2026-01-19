/**
 * Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type GraphLines, type GraphOptions } from 'cmk-shared-typing/typescript/graph_designer'

import { cmkAjax } from '@/lib/ajax'

// Copied from cmk-frontend/src/js/modules/graphs.ts

type SizePT = number

interface GraphTitleFormat {
  plain: boolean
  add_host_name: boolean
  add_host_alias: boolean
  add_service_description: boolean
}

interface GraphRenderConfig {
  border_width: number
  color_gradient: number
  editing: boolean
  explicit_title: string | null
  fixed_timerange: boolean
  font_size: SizePT
  foreground_color: string
  interaction: boolean
  onclick: string | null
  preview: boolean
  resizable: boolean
  show_controls: boolean
  show_graph_time: boolean
  show_legend: boolean
  show_margin: boolean
  show_pin: boolean
  show_time_axis: boolean
  show_time_range_previews: boolean
  show_title: boolean | 'inline'
  show_vertical_axis: boolean
  size: [bigint, bigint]
  title_format: GraphTitleFormat
  vertical_axis_width: 'fixed' | ['explicit', SizePT]
}

// eslint-disable-next-line  @typescript-eslint/no-explicit-any
type GraphRecipe = Record<string, any>

type TimeRange = [number, number]

type Seconds = number

interface GraphDataRangeMandatory {
  time_range: TimeRange
  step: Seconds | string
}

interface GraphDataRange extends GraphDataRangeMandatory {
  vertical_range: [number, number]
}

interface AjaxContext {
  graph_id: string
  definition: GraphRecipe
  data_range: GraphDataRange
  render_config: GraphRenderConfig
  display_id: string
}

type TimeSeriesValue = number | null

interface LayoutedCurveArea {
  line_type: 'area' | '-area'
  points: [TimeSeriesValue, TimeSeriesValue][]
  //dynamic
  title?: string
  color: string
}

interface LayoutedCurveStack {
  line_type: 'stack' | '-stack'
  points: [TimeSeriesValue, TimeSeriesValue][]
  //dynamic
  title?: string
  color: string
}

interface LayoutedCurveLine {
  line_type: 'line' | '-line'
  points: TimeSeriesValue[]
  //dynamic
  title?: string
  color: string
}

type LayoutedCurve = LayoutedCurveLine | LayoutedCurveArea | LayoutedCurveStack

interface HorizontalRule {
  value: number
  rendered_value: string
  color: string
  title: string
}

interface VerticalAxisLabel {
  position: number
  text: string
  line_width: number
}

interface VerticalAxis {
  range: [number, number]
  axis_label: string | null
  labels: VerticalAxisLabel[]
  max_label_length: null
  //dynamic
  pixels_per_unit: number
  pixels_per_second: number
}

interface TimeAxisLabel {
  position: number
  text: string | null
  line_width: number
}

interface TimeAxis {
  labels: TimeAxisLabel[]
  range: TimeRange
  title: string
  //dynamic
  pixels_per_second: number
}

type Timestamp = number

interface FixedVerticalRange {
  type: 'fixed'
  min: number | null
  max: number | null
}

interface MinimalVerticalRange {
  type: 'minimal'
  min: number | null
  max: number | null
}

//this type is from cmk/gui/plugins/metrics/artwork.py:82
interface GraphArtwork {
  //optional properties assigned dynamically in javascript
  id: string
  canvas_obj: HTMLCanvasElement
  ajax_context?: AjaxContext
  render_config: GraphRenderConfig
  time_origin?: number
  vertical_origin?: number
  // Labelling, size, layout
  title: string | null
  width: number
  height: number
  mirrored: boolean
  // Actual data and axes
  curves: LayoutedCurve[]
  horizontal_rules: HorizontalRule[]
  vertical_axis: VerticalAxis
  time_axis: TimeAxis
  mark_requested_end_time: boolean
  //Displayed range
  start_time: Timestamp
  end_time: Timestamp
  step: Seconds
  explicit_vertical_range: FixedVerticalRange | MinimalVerticalRange | null
  requested_vrange: [number, number] | null
  requested_start_time: Timestamp
  requested_end_time: Timestamp
  requested_step: string | Seconds
  pin_time: Timestamp | null
  // Definition itself, for reproducing the graph
  definition: GraphRecipe
  // Display id to avoid mixups in get_id_of_graph when rendering the same graph multiple times
  // in graph collections and dashboards. Often set to the empty string when not needed.
  display_id: string
}

export interface AjaxGraph {
  html: string
  graph: GraphArtwork
  context: AjaxContext
  error?: string[]
}

async function fetchAjaxGraph<OutputType>(
  graphId: string,
  graphLines: GraphLines,
  graphOptions: GraphOptions
): Promise<OutputType> {
  return cmkAjax('ajax_fetch_ajax_graph.py', {
    graph_id: graphId,
    graph_lines: graphLines,
    graph_options: graphOptions
  })
}

export type GraphRenderer = (
  graphId: string,
  graphLines: GraphLines,
  graphOptions: GraphOptions,
  container: HTMLDivElement
) => void

export async function graphRenderer(
  graphId: string,
  graphLines: GraphLines,
  graphOptions: GraphOptions,
  container: HTMLDivElement
) {
  const ajaxGraph: AjaxGraph = await fetchAjaxGraph(graphId, graphLines, graphOptions)
  // @ts-expect-error comes from different javascript file
  window['cmk'].graphs.show_ajax_graph_at_container(ajaxGraph, container)
}
