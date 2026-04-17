/**
 * Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  type Query as GraphLineQuery,
  type GraphLines,
  type GraphOptions
} from 'cmk-shared-typing/typescript/graph_designer'

import { cmkAjax } from '@/lib/ajax'

// Copied from cmk-frontend/src/js/modules/graphs.ts

type SizePT = number

interface GraphTitleFormat {
  plain: boolean
  add_host_name: boolean
  add_host_alias: boolean
  add_service_description: boolean
}

interface GraphDisplayConfigHTML {
  editing: boolean
  explicit_title: string | null
  fixed_timerange: boolean
  font_size: SizePT
  foreground_color: string
  interaction: boolean
  legend_max_height_px: number | null
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
  title_format: GraphTitleFormat
  vertical_axis_width: 'fixed' | ['explicit', SizePT]
}

// eslint-disable-next-line  @typescript-eslint/no-explicit-any
type GraphRecipe = Record<string, any>

// All frontend-mutable state; round-tripped on every AJAX call.
interface GraphInteractionState {
  graph_id: string
  consolidation_function: string | null
  time_start: number
  time_end: number
  // For forecast graphs, step is a colon-separated string "[step length]:[rrd point count]"
  step: number | string
  value_min: number | null
  value_max: number | null
  size_x: number
  size_y: number
}

interface GraphRenderState {
  interaction: GraphInteractionState
  recipe: GraphRecipe
  specification: object
  display_config: GraphDisplayConfigHTML
  display_id: string
  onclick: string | null
}

interface LayoutedCurveArea {
  line_type: 'area' | '-area'
  points: [number | null, number | null][]
  //dynamic
  title?: string
  color: string
}

interface LayoutedCurveStack {
  line_type: 'stack' | '-stack'
  points: [number | null, number | null][]
  //dynamic
  title?: string
  color: string
}

interface LayoutedCurveLine {
  line_type: 'line' | '-line'
  points: (number | null)[]
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

interface AxisTick {
  position: number
  text: string | null
  line_width: number
}

interface YAxis {
  min: number
  max: number
  labels: AxisTick[]
  //dynamic
  pixels_per_unit: number
}

interface XAxis {
  labels: AxisTick[]
  start: number
  end: number
}

//this type is from cmk/gui/plugins/metrics/artwork.py:82
interface ActualTimeRange {
  start: number
  end: number
  step: number
}

interface RequestedTimeRange {
  start: number
  end: number
}

interface GraphArtwork {
  curves: LayoutedCurve[]
  horizontal_rules: HorizontalRule[]
  y_axis: YAxis
  x_axis: XAxis
  mark_requested_end_time: boolean
  //Displayed range
  actual_time: ActualTimeRange
  requested_time: RequestedTimeRange
  requested_y_range: [number, number] | null
  pin_time: number | null
}

export interface AjaxGraph {
  html: string
  graph: GraphArtwork
  context: GraphRenderState
  error?: string
  warning?: string
  queries_reached_limit?: GraphLineQuery[]
}

export async function fetchAjaxGraph<OutputType>(
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

export type GraphRenderer = (ajaxGraph: AjaxGraph, container: HTMLDivElement) => void

export async function graphRenderer(ajaxGraph: AjaxGraph, container: HTMLDivElement) {
  // @ts-expect-error comes from different javascript file
  window['cmk'].graphs.show_ajax_graph_at_container(ajaxGraph, container)
}
