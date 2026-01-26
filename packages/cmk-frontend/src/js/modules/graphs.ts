/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { call_ajax } from './ajax'
import { add, hide, show, update_content } from './hover'
import { pause } from './reload_pause'
import {
  add_class,
  add_event_handler,
  content_scrollbar,
  current_script,
  execute_javascript_by_object,
  has_class,
  is_in_viewport,
  makeuri,
  prevent_default_events,
  wheel_event_delta,
  wheel_event_name
} from './utils'

//types from cmk/utils/type_defs/_misc.py:81
type Timestamp = number
type Seconds = number
type TimeRange = [number, number]
export type TimeSeriesValue = number | null
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

interface _GraphDataRangeMandatory {
  time_range: TimeRange
  step: Seconds | string
}

interface GraphDataRange extends _GraphDataRangeMandatory {
  vertical_range: [number, number]
}

interface AjaxContext {
  graph_id: string
  definition: GraphRecipe
  data_range: GraphDataRange
  render_config: GraphRenderConfig
  display_id: string
}

export interface AjaxGraph {
  html: string
  graph: GraphArtwork
  context: AjaxContext
  error?: string
}

interface LayoutedCurveArea {
  line_type: 'area' | '-area'
  points: [TimeSeriesValue, TimeSeriesValue][]
  attributes: Record<string, string>
  //dynamic
  title?: string
  color: string
}

interface LayoutedCurveStack {
  line_type: 'stack' | '-stack'
  points: [TimeSeriesValue, TimeSeriesValue][]
  attributes: Record<string, string>
  //dynamic
  title?: string
  color: string
}

interface LayoutedCurveLine {
  line_type: 'line' | '-line'
  points: TimeSeriesValue[]
  attributes: Record<string, string>
  //dynamic
  title?: string
  color: string
}

export type LayoutedCurve = LayoutedCurveLine | LayoutedCurveArea | LayoutedCurveStack

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

type GraphRecipe = Record<string, any>

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

export interface HorizontalRule {
  value: number
  rendered_value: string
  color: string
  title: string
}

//this type is from cmk/gui/plugins/metrics/artwork.py:82
export interface GraphArtwork {
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

// Styling. Please note that for each visible pixel our canvas
// has two pixels. This improves the resolution when zooming
// in with your browser.
const v_label_margin = 10 // pixels between vertical label and v axis
const t_label_margin = 10 // pixels between time label and t axis
const axis_over_width = 5 // pixel that the axis is longer for optical reasons
const curve_line_width = 2.0
const rule_line_width = 2.0
const g_page_update_delay = 60 // prevent page update for X seconds
const g_delayed_graphs: DelayedGraph[] = []

// Global graph constructs to store the graphs etc.
const g_graphs: Record<string, GraphArtwork> = {}
let g_current_graph_id = 0

interface DelayedGraph {
  graph_load_container: HTMLElement | Node | null
  graph_recipe: GraphRecipe
  graph_data_range: GraphDataRange
  graph_render_config: GraphRenderConfig
  script_object: HTMLScriptElement
  graph_display_id: string
}

//#   .-Creation-----------------------------------------------------------.
//#   |              ____                _   _                             |
//#   |             / ___|_ __ ___  __ _| |_(_) ___  _ __                  |
//#   |            | |   | '__/ _ \/ _` | __| |/ _ \| '_ \                 |
//#   |            | |___| | |  __/ (_| | |_| | (_) | | | |                |
//#   |             \____|_|  \___|\__,_|\__|_|\___/|_| |_|                |
//#   |                                                                    |
//#   +--------------------------------------------------------------------+
//#   | Graphs are created by a javascript function. The unique graph id   |
//#   | is create solely by the javascript code. This function is being    |
//#   | called by web/plugins/graphs.py:render_graphs_htmls()              |
//#   '--------------------------------------------------------------------'

function get_id_of_graph(ajax_context: AjaxContext) {
  // Return the graph_id for and eventual existing graph
  for (const graph_id in g_graphs) {
    // JSON.stringify seems to be the easiest way to compare the both dicts
    if (
      JSON.stringify(ajax_context.definition.specification) ==
        JSON.stringify(g_graphs[graph_id].ajax_context!.definition.specification) &&
      JSON.stringify(ajax_context.render_config) ==
        JSON.stringify(g_graphs[graph_id].ajax_context!.render_config) &&
      ajax_context.display_id == g_graphs[graph_id].ajax_context!.display_id
    ) {
      return graph_id
    }
  }

  // Otherwise create a new graph
  return 'graph_' + g_current_graph_id++
}

function show_error(container: HTMLDivElement, msg: string) {
  let element = document.getElementById('error_container')
  if (element === null) {
    element = document.createElement('div')
    element.id = 'error_container'
    element.className = 'error'
    container.parentNode!.insertBefore(element, container)
  }
  element.innerHTML = msg
}

export function show_ajax_graph_at_container(ajax_graph: AjaxGraph, container: HTMLDivElement) {
  // Detect whether or not a new graph_id has to be calculated. During the view
  // data reload create_graph() is called again for all already existing graphs.
  // In this situation the graph_id needs to be detected and reused instead of
  // calculating a new one. Otherwise e.g. g_graphs will grow continously.
  const error = ajax_graph['error']
  if (error) {
    show_error(container, error)
  }
  const ajax_context = ajax_graph['context']
  const graph_id = get_id_of_graph(ajax_context)

  container.setAttribute('id', graph_id)
  container.className = 'graph_container'
  container.innerHTML = ajax_graph['html']

  const embedded_script = document.createElement('script')
  container.parentNode!.appendChild(embedded_script)

  // Now register and paint the graph
  ajax_context['graph_id'] = graph_id
  //TODO: perhaps reformat this so we have two GraphArtwork interfaces
  // before and after these assignments
  g_graphs[graph_id] = ajax_graph['graph']
  g_graphs[graph_id]['ajax_context'] = ajax_context
  g_graphs[graph_id]['render_config'] = ajax_graph['context']['render_config']
  g_graphs[graph_id]['id'] = graph_id
  render_graph(g_graphs[graph_id])
}

export function create_graph(
  html_code: string,
  graph_artwork: GraphArtwork,
  graph_render_config: GraphRenderConfig,
  ajax_context: AjaxContext
) {
  // Detect whether or not a new graph_id has to be calculated. During the view
  // data reload create_graph() is called again for all already existing graphs.
  // In this situation the graph_id needs to be detected and reused instead of
  // calculating a new one. Otherwise e.g. g_graphs will grow continously.
  const graph_id = get_id_of_graph(ajax_context)

  // create container div that contains the graph.
  const container_div = document.createElement('div')
  container_div.setAttribute('id', graph_id)
  /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
  container_div.innerHTML = html_code
  if (graph_render_config.show_time_range_previews)
    container_div.className = 'graph_container timeranges'
  else container_div.className = 'graph_container'

  const embedded_script = get_current_script()

  // Insert the new container right after the script tag
  // @ts-ignore
  embedded_script.parentNode.insertBefore(container_div, embedded_script.nextSibling)

  // Now register and paint the graph
  ajax_context['graph_id'] = graph_id
  //TODO: perhaps reformat this so we have two GraphArtwork interfaces
  // before and after these assignments
  g_graphs[graph_id] = graph_artwork
  g_graphs[graph_id]['ajax_context'] = ajax_context
  g_graphs[graph_id]['render_config'] = graph_render_config
  g_graphs[graph_id]['id'] = graph_id
  render_graph(g_graphs[graph_id])
}

// determine DOM node of the <javascript> that called us. It's
// parent will get the graph node attached.
function get_current_script(): HTMLScriptElement {
  const embedded_script = current_script
  if (embedded_script) return embedded_script

  //TODO: delete following statement since we don't support IE anymore
  // The function fixes IE compatibility issues
  //@ts-ignore
  return (
    document.currentScript ||
    (function () {
      // eslint-disable-line
      const scripts = document.getElementsByTagName('script')
      return scripts[scripts.length - 1]
    })()
  )
}

// Is called from the HTML code rendered with python. It contacts
// the python code again via an AJAX call to get the rendered graph.
//
// This is done for the following reasons:
//
// a) Start rendering and updating a graph in the moment it gets visible to the
//    user for the first time.
// b) Process the rendering asynchronous via javascript to make the page loading
//    faster by parallelizing the graph loading processes.
export function load_graph_content(
  graph_recipe: GraphRecipe,
  graph_data_range: GraphDataRange,
  graph_render_config: GraphRenderConfig,
  graph_display_id: string
) {
  const script_object = get_current_script()

  // In case the graph load container (-> is at future graph location) is not
  // visible to the user delay processing of this function
  const graph_load_container = script_object.previousSibling
  if (!is_in_viewport(graph_load_container as HTMLElement)) {
    g_delayed_graphs.push({
      graph_load_container: graph_load_container,
      graph_recipe: graph_recipe,
      graph_data_range: graph_data_range,
      graph_render_config: graph_render_config,
      script_object: script_object,
      graph_display_id: graph_display_id
    })
    return
  } else {
    do_load_graph_content(
      graph_recipe,
      graph_data_range,
      graph_render_config,
      script_object,
      graph_display_id
    )
  }
}

export function register_delayed_graph_listener() {
  const num_delayed = g_delayed_graphs.length
  if (num_delayed == 0) return // no delayed graphs: Nothing to do

  // Start of delayed graph renderer listening
  // @ts-ignore
  // TODO replace content scrollbar with two functions
  // create_content_scrollbar if no parameter is given
  // get_content_scrollbar if it is given

  // if the graph is rendered in a dashlet, we have to use the scrollbar of
  // the dashlet
  const dashletElement = document.getElementById('dashlet_content_wrapper')

  const scrollbar = content_scrollbar(dashletElement ? 'dashlet_content_wrapper' : '')

  scrollbar?.getScrollElement()?.addEventListener('scroll', delayed_graph_renderer)

  add_event_handler('resize', delayed_graph_renderer)
}

function do_load_graph_content(
  graph_recipe: GraphRecipe,
  graph_data_range: GraphDataRange,
  graph_render_config: GraphRenderConfig,
  script_object: HTMLScriptElement,
  graph_display_id: string
) {
  const graph_load_container = script_object.previousSibling as HTMLElement
  update_graph_load_container(
    graph_load_container,
    'Loading graph...',
    '<img class="loading" src="themes/facelift/images/load_graph.png">'
  )

  const post_data =
    'request=' +
    encodeURIComponent(
      JSON.stringify({
        graph_recipe: graph_recipe,
        graph_data_range: graph_data_range,
        graph_render_config: graph_render_config,
        graph_display_id: graph_display_id
      })
    )

  call_ajax('ajax_render_graph_content.py', {
    method: 'POST',
    post_data: post_data,
    response_handler: handle_load_graph_content,
    error_handler: handle_load_graph_content_error,
    handler_data: script_object
  })
}

function handle_load_graph_content(script_object: HTMLOrSVGScriptElement, ajax_response: string) {
  const response = JSON.parse(ajax_response)

  if (response.result_code != 0) {
    handle_load_graph_content_error(script_object, response.result_code, response.result)
    return
  }

  // Create a temporary div node to load the response into the DOM.
  // Then get the just loaded graph objects from the temporary div and
  // add replace the placeholder with it.
  const tmp_div = document.createElement('div')
  /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
  tmp_div.innerHTML = response.result

  script_object.parentNode!.replaceChild(tmp_div, script_object.previousSibling!)
  script_object.parentNode!.removeChild(script_object)
  execute_javascript_by_object(tmp_div)
}

function handle_load_graph_content_error(
  script_object: HTMLOrSVGScriptElement,
  status_code: number,
  error_msg: string
) {
  const msg = 'Loading graph failed: (Status: ' + status_code + ')<br><br>' + error_msg

  const graph_load_container = script_object.previousSibling as HTMLElement
  update_graph_load_container(graph_load_container, 'ERROR', '<pre>' + msg + '</pre>')
}

function update_graph_load_container(container: HTMLElement, title: string, content_html: string) {
  /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
  ;(container.getElementsByClassName('title')[0] as HTMLElement).innerText = title
  /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
  container.getElementsByClassName('content')[0].innerHTML = content_html
}

// Is executed on scroll / resize events in case at least one graph is
// using the delayed graph rendering mechanism
function delayed_graph_renderer() {
  const num_delayed = g_delayed_graphs.length
  if (num_delayed == 0) return // no delayed graphs: Nothing to do

  let i = num_delayed
  while (i--) {
    const entry = g_delayed_graphs[i]
    if (is_in_viewport(entry.graph_load_container as HTMLElement)) {
      do_load_graph_content(
        entry.graph_recipe,
        entry.graph_data_range,
        entry.graph_render_config,
        entry.script_object,
        entry.graph_display_id
      )
      g_delayed_graphs.splice(i, 1)
    }
  }
  return true
}

function update_delayed_graphs_timerange(start_time: number, end_time: number) {
  for (let i = 0, len = g_delayed_graphs.length; i < len; i++) {
    const entry = g_delayed_graphs[i]
    entry.graph_data_range.time_range = [start_time, end_time]
  }
}

//#.
//#   .-Painting-------------------------------------------------------------.
//#   |                ____       _       _   _                              |
//#   |               |  _ \ __ _(_)_ __ | |_(_)_ __   __ _                  |
//#   |               | |_) / _` | | '_ \| __| | '_ \ / _` |                 |
//#   |               |  __/ (_| | | | | | |_| | | | | (_| |                 |
//#   |               |_|   \__,_|_|_| |_|\__|_|_| |_|\__, |                 |
//#   |                                               |___/                  |
//#   +----------------------------------------------------------------------+
//#   |  Paint the graph into the canvas object.                             |
//#   '----------------------------------------------------------------------'

// Keep draw contex as global variable for conveniance
let ctx: null | CanvasRenderingContext2D = null

// Notes:
// - In JS canvas 0,0 is at top left
// - We paint as few padding as possible. Additional padding is being
//   added via CSS
// NOTE: If you change something here, then please check if you also need to
// adapt the Python code that creates that graph_artwork
function render_graph(graph: GraphArtwork) {
  // First find the canvas object and add a reference to the graph dict
  // If the initial rendering failed then any later update does not
  // make any sense.
  const container = document.getElementById(graph['id']!)
  if (!container) return

  const canvas = (container.childNodes[0] as HTMLElement).getElementsByTagName('canvas')[0]
  if (!canvas) return

  update_graph_styling(graph, container)

  graph['canvas_obj'] = canvas

  ctx = canvas.getContext('2d') // Create one ctx for all operations

  if (!ctx) throw new Error("ctx shouldn't be null!")

  const font_size = from_display_coord(graph.render_config.font_size)
  ctx.font = font_size + 'pt sans-serif'

  const width = canvas.width
  const height = canvas.height

  const bottom_border = graph_bottom_border(graph)
  let top_border = 0
  if (bottom_border > 0) top_border = (bottom_border - t_label_margin) / 2

  const v_axis_width = graph_vertical_axis_width(graph)

  const v_line_color = [graph.render_config.foreground_color, '#8097b19c', '#8097b19c']

  // Prepare position and translation of origin
  const t_range_from = graph['time_axis']['range'][0]
  const t_range_to = graph['time_axis']['range'][1]
  const t_range = t_range_to - t_range_from
  const t_pixels = width - v_axis_width
  const t_pixels_per_second = t_pixels / t_range
  graph['time_axis']['pixels_per_second'] = t_pixels_per_second // store for dragging

  const v_range_from = graph['vertical_axis']['range'][0]
  const v_range_to = graph['vertical_axis']['range'][1]
  const v_range = v_range_to - v_range_from
  const v_pixels = height - bottom_border - top_border
  const v_pixels_per_unit = v_pixels / v_range
  graph['vertical_axis']['pixels_per_unit'] = v_pixels_per_unit // store for dragging

  const t_orig = v_axis_width
  graph['time_origin'] = t_orig // for dragging

  const v_orig = height - bottom_border
  graph['vertical_origin'] = v_orig // for dragging

  const v_axis_orig = v_range_from

  // Now transform the whole coordinate system to our real t and v coords
  // so if we paint something at (0, 0) it will correctly represent a
  // value of 0 and a time point of time_start.
  const coordinate_trans = new GraphCoordinateTransformation(
    t_orig,
    t_range_from,
    t_pixels_per_second,
    v_orig,
    v_axis_orig,
    v_pixels_per_unit
  )

  // render grid
  if (!graph.render_config.preview) {
    // Paint the vertical axis
    let vertical_axis_label
    const vertical_axis_labels = graph['vertical_axis']['labels']
    ctx.save()
    ctx.textAlign = 'end'
    ctx.textBaseline = 'middle'
    ctx.fillStyle = graph.render_config.foreground_color
    for (let i = 0; i < vertical_axis_labels.length; i++) {
      vertical_axis_label = vertical_axis_labels[i]
      if (vertical_axis_label.line_width > 0) {
        paint_line(
          coordinate_trans.trans(t_range_from, vertical_axis_label.position),
          coordinate_trans.trans(t_range_to, vertical_axis_label.position),
          v_line_color[vertical_axis_label.line_width]
        )
      }

      if (graph.render_config.show_vertical_axis)
        ctx.fillText(
          vertical_axis_label.text,
          t_orig - v_label_margin,
          coordinate_trans.trans(t_range_from, vertical_axis_label.position)[1]
        )
    }
    ctx.restore()

    // Paint time axis
    let time_axis_label
    const time_axis_labels = graph['time_axis']['labels']
    ctx.save()
    ctx.fillStyle = graph.render_config.foreground_color
    for (let i = 0; i < time_axis_labels.length; i++) {
      time_axis_label = time_axis_labels[i]
      if (time_axis_label.line_width > 0) {
        paint_line(
          coordinate_trans.trans(time_axis_label.position, v_range_from),
          coordinate_trans.trans(time_axis_label.position, v_range_to),
          v_line_color[time_axis_label.line_width]
        )
      }
    }
    ctx.restore()
  }

  ctx.save()

  ctx.beginPath()
  ctx.rect(
    coordinate_trans.trans_t(t_range_from),
    coordinate_trans.trans_v(v_range_to),
    t_range * t_pixels_per_second,
    v_range * v_pixels_per_unit
  )
  ctx.clip()

  // Paint curves
  const curves = graph['curves']
  const step = graph['step'] / 2.0
  let color, opacity
  for (let i = 0; i < curves.length; i++) {
    const curve = curves[i]
    const points = curve['points']
    // the hex color code can have additional opacity information
    // if these are none existing default to 0.3 UX project
    if (curve['color'].length == 9) {
      color = curve['color'].substr(0, 7)
      opacity = curve['color'].slice(-2)
    } else {
      color = curve['color']
      opacity = '4c' // that is 0.3
    }

    if (
      curve['line_type'] == 'area' ||
      curve['line_type'] == '-area' ||
      curve['line_type'] == 'stack' ||
      curve['line_type'] == '-stack'
    ) {
      const corner_markers = points as [TimeSeriesValue, TimeSeriesValue][]

      ctx.fillStyle = hex_to_rgba(color + opacity)
      ctx.imageSmoothingEnabled = true // seems no difference on FF
      ctx.strokeStyle = color
      ctx.lineWidth = curve_line_width
      render_curve(
        graph['start_time'],
        step,
        coordinate_trans,
        corner_markers.map(([lower, upper]) => {
          if (lower == null || upper == null) {
            return null
          } else {
            return upper <= 0 ? lower : upper
          }
        }),
        ctx
      )
      render_area(graph['start_time'], step, coordinate_trans, corner_markers, ctx)
    } else if (curve['line_type'] == 'line' || curve['line_type'] == '-line') {
      ctx.strokeStyle = color
      ctx.lineWidth = curve_line_width
      render_curve(graph['start_time'], step, coordinate_trans, points as TimeSeriesValue[], ctx)
    }
  }
  ctx.restore()

  if (!graph.render_config.preview && graph.render_config.show_time_axis) {
    // Paint time axis labels
    ctx.save()
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    ctx.fillStyle = graph.render_config.foreground_color
    const labels = graph['time_axis']['labels']
    labels.forEach((time_axis_label) => {
      if (time_axis_label.text != null) {
        // @ts-ignore
        ctx.fillText(
          time_axis_label.text,
          coordinate_trans.trans(time_axis_label.position, 0)[0],
          v_orig + t_label_margin
        )
      }
    })
    ctx.restore()
  }

  // Paint horizontal rules like warn and crit
  ctx.save()
  ctx.lineWidth = rule_line_width
  for (const horizontal_rule of graph.horizontal_rules) {
    if (horizontal_rule.value >= v_range_from && horizontal_rule.value <= v_range_to) {
      paint_line(
        coordinate_trans.trans(t_range_from, horizontal_rule.value),
        coordinate_trans.trans(t_range_to, horizontal_rule.value),
        horizontal_rule.color
      )
    }
  }
  ctx.restore()

  // paint the optional pin
  if (graph.render_config.show_pin && graph.pin_time != null) {
    const pin_x = coordinate_trans.trans_t(graph.pin_time)
    if (pin_x >= t_orig) {
      paint_line(
        [pin_x, v_orig + axis_over_width],
        [pin_x, 0],
        graph.render_config.foreground_color
      )
      paint_dot([pin_x, 0], graph.render_config.foreground_color)
    }
  }
  // paint forecast graph future start
  if (graph.mark_requested_end_time) {
    const pin_x = coordinate_trans.trans_t(graph.requested_end_time)
    if (pin_x >= t_orig) {
      paint_line([pin_x, v_orig + axis_over_width], [pin_x, 0], '#00ff00')
    }
  }

  // Enable interactive mouse control of graph
  graph_activate_mouse_control(graph)
}

// Transforms the graph coordinate system to our real t and v coordinates.
// (0, 0) is at the top left corner of the canvas.
class GraphCoordinateTransformation {
  t_orig: number
  t_range_from: number
  t_pixels_per_second: number
  v_orig: number
  v_axis_orig: number
  v_pixels_per_unit: number

  constructor(
    t_orig: number,
    t_range_from: number,
    t_pixels_per_second: number,
    v_orig: number,
    v_axis_orig: number,
    v_pixels_per_unit: number
  ) {
    this.t_orig = t_orig
    this.t_range_from = t_range_from
    this.t_pixels_per_second = t_pixels_per_second
    this.v_orig = v_orig
    this.v_axis_orig = v_axis_orig
    this.v_pixels_per_unit = v_pixels_per_unit
  }

  trans_t(t: number): number {
    return (t - this.t_range_from) * this.t_pixels_per_second + this.t_orig
  }

  trans_v(v: number): number {
    return this.v_orig - (v - this.v_axis_orig) * this.v_pixels_per_unit
  }

  trans(t: number, v: number): [number, number] {
    return [this.trans_t(t), this.trans_v(v)]
  }
}

function render_curve(
  start_time: number,
  time_step_size: number,
  coordinate_tranformation: GraphCoordinateTransformation,
  v_points: TimeSeriesValue[],
  ctx: CanvasRenderingContext2D
) {
  let t = start_time
  let should_connect_to_previous_point = false

  ctx.beginPath()

  for (const v_value of v_points) {
    if (v_value == null) {
      should_connect_to_previous_point = false
      t += time_step_size
      continue
    }

    const p = coordinate_tranformation.trans(t, v_value)
    if (should_connect_to_previous_point) {
      ctx.lineTo(p[0], p[1])
    } else {
      ctx.moveTo(p[0], p[1])
    }
    should_connect_to_previous_point = true
    t += time_step_size
  }

  ctx.stroke()
  ctx.closePath()
}

function render_area(
  start_time: number,
  time_step_size: number,
  coordinate_tranformation: GraphCoordinateTransformation,
  corner_markers: [TimeSeriesValue, TimeSeriesValue][],
  ctx: CanvasRenderingContext2D
) {
  let t = start_time
  let prev_lower: TimeSeriesValue = null
  let prev_upper: TimeSeriesValue = null

  for (const [lower, upper] of corner_markers) {
    if (lower == null || upper == null || prev_lower == null || prev_upper == null) {
      prev_lower = lower
      prev_upper = upper
      t += time_step_size
      continue
    }

    render_filled_polygon(
      ctx,
      coordinate_tranformation,
      [t - time_step_size, prev_lower],
      [t - time_step_size, prev_upper],
      [t, upper],
      [t, lower]
    )

    prev_lower = lower
    prev_upper = upper
    t += time_step_size
  }
}

function render_filled_polygon(
  ctx: CanvasRenderingContext2D,
  coordinate_tranformation: GraphCoordinateTransformation,
  ...corner_coordinates: [number, number][]
) {
  if (!corner_coordinates.length) return

  ctx.beginPath()
  ctx.moveTo(
    coordinate_tranformation.trans_t(corner_coordinates[0][0]),
    coordinate_tranformation.trans_v(corner_coordinates[0][1])
  )
  for (const corner_coord of corner_coordinates.slice(1)) {
    ctx.lineTo(
      coordinate_tranformation.trans_t(corner_coord[0]),
      coordinate_tranformation.trans_v(corner_coord[1])
    )
  }
  ctx.closePath()
  ctx.fill()
}

function hex_to_rgba(color: string) {
  // convert '#00112233' to 'rgba(0, 17, 34, 0.2)'
  // NOTE: When we drop IE11 support we don't need this conversion anymore.
  const parse = (x: number) => parseInt(color.substr(x, 2), 16)
  return `rgba(${parse(1)}, ${parse(3)}, ${parse(5)}, ${parse(7) / 255})`
}

function graph_vertical_axis_width(graph: GraphArtwork) {
  if (graph.render_config.preview) return 0

  if (!graph.render_config.show_vertical_axis && !graph.render_config.show_controls) return 0

  if (
    graph.render_config.vertical_axis_width instanceof Array &&
    graph.render_config.vertical_axis_width[0] == 'explicit'
  ) {
    return from_display_coord(pt_to_px(graph.render_config.vertical_axis_width[1]))
  }

  return 6 * from_display_coord(pt_to_px(graph.render_config.font_size))
}

function update_graph_styling(graph: GraphArtwork, container: HTMLElement) {
  const graph_div = container.getElementsByClassName('graph')[0] as HTMLElement
  if (!graph_div) return
  graph_div.style.color = graph.render_config.foreground_color

  const inverted_fg_color = render_color(
    invert_color(parse_color(graph.render_config.foreground_color))
  )

  const style = document.createElement('style')
  const rules = [
    {
      selector: 'div.graph div.v_axis_label',
      attrs: {
        color: render_color_rgba(parse_color(graph.render_config.foreground_color), 0.8)
      }
    },
    {
      selector: 'div.graph div.time',
      attrs: {
        color: render_color_rgba(parse_color(graph.render_config.foreground_color), 0.8)
      }
    },
    {
      selector:
        'div.graph table.legend th.scalar.inactive, div.graph table.legend td.scalar.inactive',
      attrs: {
        color: render_color_rgba(parse_color(graph.render_config.foreground_color), 0.6)
      }
    },
    {
      selector: 'div.graph table.legend th',
      attrs: {
        'border-bottom': '1px solid ' + graph.render_config.foreground_color
      }
    },
    {
      selector: 'div.graph table.legend th.scalar',
      attrs: {
        color: graph.render_config.foreground_color,
        'border-bottom': '1px solid ' + graph.render_config.foreground_color
      }
    },
    {
      selector: 'div.graph a',
      attrs: {
        color: graph.render_config.foreground_color
      }
    },
    {
      selector: 'div.graph.preview .title',
      attrs: {
        'text-shadow':
          '-1px 0 ' +
          inverted_fg_color +
          ', 0 1px ' +
          inverted_fg_color +
          ', 1px 0 ' +
          inverted_fg_color +
          ', 0 -1px ' +
          inverted_fg_color
      }
    },
    {
      selector: 'div.graph div.title.inline, div.graph div.time.inline',
      attrs: {
        'text-shadow':
          '-1px 0 ' +
          inverted_fg_color +
          ', 0 1px ' +
          inverted_fg_color +
          ', 1px 0 ' +
          inverted_fg_color +
          ', 0 -1px ' +
          inverted_fg_color
      }
    },
    {
      selector: 'div.graph div.indicator',
      attrs: {
        'border-right': '1px dotted ' + graph.render_config.foreground_color
      }
    }
  ]

  let css_text = ''
  for (let i = 0, len = rules.length; i < len; i++) {
    const spec = rules[i]
    css_text += spec['selector'] + ' {\n'
    for (const attr_name in spec['attrs']) {
      //@ts-ignore
      css_text += attr_name + ': ' + spec['attrs'][attr_name] + ';\n'
    }
    css_text += '}\n'
  }

  /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
  style.innerHTML = css_text
  graph_div.appendChild(style)
}

function pt_to_px(size: number) {
  return (size / 72.0) * 96
}

function to_display_coord(canvas_coord: number) {
  return canvas_coord / 2
}

function from_display_coord(display_coord: number) {
  return display_coord * 2
}

function graph_bottom_border(graph: GraphArtwork) {
  if (graph.render_config.preview) return 0

  if (graph.render_config.show_time_axis)
    return from_display_coord(pt_to_px(graph.render_config.font_size)) + t_label_margin
  else return 0
}

function paint_line(p0: [number, number], p1: [number, number], color: string) {
  if (!ctx) throw new Error("ctx shouldn't be null!")
  ctx.save()
  ctx.strokeStyle = color
  ctx.beginPath()
  ctx.moveTo(p0[0], p0[1])
  ctx.lineTo(p1[0], p1[1])
  ctx.stroke()
  ctx.closePath()
  ctx.restore()
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function paint_rect(p: [number, number], width: number, height: number, color: string) {
  if (!ctx) throw new Error("ctx shouldn't be null!")
  ctx.save()
  ctx.fillStyle = color
  ctx.fillRect(p[0], p[1], width, height)
  ctx.restore()
}

function paint_dot(p: [number, number], color: string) {
  if (!ctx) throw new Error("ctx shouldn't be null!")
  ctx.save()
  ctx.beginPath()
  ctx.arc(p[0], p[1], 5, 0, 2 * Math.PI)
  ctx.fillStyle = color
  ctx.fill()
  ctx.closePath()
  ctx.restore()
}

function parse_color(hexcolor: string): [number, number, number] {
  const bits = parseInt(hexcolor.substr(1), 16)
  const r = ((bits >> 16) & 255) / 255.0
  const g = ((bits >> 8) & 255) / 255.0
  const b = (bits & 255) / 255.0
  return [r, g, b]
}

function render_color(rgb: [number, number, number]) {
  const r = rgb[0]
  const g = rgb[1]
  const b = rgb[2]
  const bits = Math.trunc(b * 255 + 256 * (g * 255) + 65536 * (r * 255))
  let hex = bits.toString(16)
  while (hex.length < 6) hex = '0' + hex
  return '#' + hex
}

function render_color_rgba(rgb: [number, number, number], a: number) {
  const r = rgb[0] * 255
  const g = rgb[1] * 255
  const b = rgb[2] * 255
  return 'rgba(' + r + ', ' + g + ', ' + b + ', ' + a + ')'
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function lighten_color(rgb: [number, number, number], v: number) {
  const lighten = function (x: number, v: number) {
    return x + (1.0 - x) * v
  }
  return [lighten(rgb[0], v), lighten(rgb[1], v), lighten(rgb[2], v)]
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function darken_color(rgb: [number, number, number], v: number) {
  const darken = function (x: number, v: number) {
    return x * (1.0 - v)
  }
  return [darken(rgb[0], v), darken(rgb[1], v), darken(rgb[2], v)]
}

function invert_color(rgb: [number, number, number]): [number, number, number] {
  const invert = function (x: number) {
    return 1.0 - x
  }
  return [invert(rgb[0]), invert(rgb[1]), invert(rgb[2])]
}

//#.
//#   .-Mouse Control--------------------------------------------------------.
//#   |   __  __                         ____            _             _     |
//#   |  |  \/  | ___  _   _ ___  ___   / ___|___  _ __ | |_ _ __ ___ | |    |
//#   |  | |\/| |/ _ \| | | / __|/ _ \ | |   / _ \| '_ \| __| '__/ _ \| |    |
//#   |  | |  | | (_) | |_| \__ \  __/ | |__| (_) | | | | |_| | | (_) | |    |
//#   |  |_|  |_|\___/ \__,_|___/\___|  \____\___/|_| |_|\__|_|  \___/|_|    |
//#   |                                                                      |
//#   +----------------------------------------------------------------------+
//#   |  Code for handling dragging and zooming via the scroll whell.        |
//#   '----------------------------------------------------------------------'

let g_dragging_graph: null | {
  pos: [number, number]
  graph: GraphArtwork
} = null
let g_resizing_graph: null | {
  pos: [number, number]
  graph: GraphArtwork
} = null
// Is set to True when one graph is started being updated via AJAX.
// It is set to False when the update has finished.
let g_graph_update_in_process = false

// Is set to True when one graph is started being updated via AJAX. It is
// set to False after 100 ms to prevent too often graph rendering updates.
let g_graph_in_cooldown_period = false

// Holds the timeout object which triggers an AJAX update of all other graphs
// on the page 500ms after the last mouse wheel zoom step.
let g_graph_wheel_timeout: null | number = null

// Returns the graph container node. Can be called with any DOM node as
// parameter which is part of a graph
//TODO the three functions below behave similarly but have only different css_class
// so we only need one and the rest should be deleted
function get_graph_container(obj: HTMLElement) {
  let newObj: null | HTMLElement = obj
  while (newObj && !has_class(newObj, 'graph_container'))
    newObj = newObj.parentNode as HTMLElement | null
  return newObj
}

function get_main_graph_container(obj: HTMLElement) {
  let res: HTMLElement | null = obj
  while (res && !has_class(res, 'graph_with_timeranges')) res = res.parentNode as HTMLElement | null
  return res!.childNodes[1] as HTMLElement
}

function get_graph_graph_node(obj: HTMLElement) {
  let res: HTMLElement | null = obj
  while (res && !has_class(res, 'graph')) res = res.parentNode as HTMLElement | null
  return res
}

// Walk up DOM parents to find the graph container, then walk down to
// find the canvas element which has the graph_id in it's id attribute.
// Strip off the graph_id and return it.
function get_graph_id_of_dom_node(target: HTMLElement) {
  const graph_container = get_graph_container(target)
  if (!graph_container) return null

  return graph_container.id
}

function graph_global_mouse_wheel(event: Event): boolean | void {
  let obj: HTMLElement | ParentNode | null = event!.target as HTMLElement
  // prevent page scrolling when making wheelies over graphs
  while (obj instanceof HTMLElement && !obj.className) obj = obj.parentNode
  if (obj instanceof HTMLElement && obj.tagName == 'DIV' && obj.className == 'graph_container')
    return prevent_default_events(event!)
}

function graph_activate_mouse_control(graph: GraphArtwork) {
  const canvas = graph['canvas_obj']
  add_event_handler(
    'mousemove',
    function (event) {
      return graph_mouse_move(event as MouseEvent, graph)
    },
    canvas
  )

  add_event_handler(
    'mousedown',
    function (event) {
      return graph_mouse_down(event, graph)
    },
    canvas
  )

  const on_wheel = function (event: Event) {
    return graph_mouse_wheel(event, graph)
  }

  add_event_handler(wheel_event_name(), on_wheel, canvas)
  add_event_handler(wheel_event_name(), graph_global_mouse_wheel)

  add_event_handler('mouseup', global_graph_mouse_up)

  if (
    graph.ajax_context!.render_config.show_controls &&
    graph.ajax_context!.render_config.resizable
  ) {
    // Find resize img element
    const container = get_graph_container(canvas)
    const resize_img = container!.getElementsByClassName('resize')[0]
    add_event_handler(
      'mousedown',
      function (event) {
        return graph_start_resize(event as MouseEvent, graph)
      },
      resize_img
    )

    add_event_handler('mousemove', graph_mouse_resize)
  }

  if (graph.ajax_context!.render_config.interaction) {
    add_event_handler('mousemove', update_mouse_hovering)
  }
}

function graph_start_resize(event: MouseEvent, graph: GraphArtwork) {
  g_resizing_graph = {
    pos: [event.clientX, event.clientY],
    graph: graph
  }
  return prevent_default_events(event)
}

function graph_mouse_resize(event: Event) {
  if (!g_resizing_graph) return true

  if (g_graph_update_in_process || g_graph_in_cooldown_period) return prevent_default_events(event)

  const mouseEvent = event as MouseEvent
  const new_x = mouseEvent.clientX
  const new_y = mouseEvent.clientY
  const delta_x = new_x - g_resizing_graph.pos[0]
  const delta_y = new_y - g_resizing_graph.pos[1]
  g_resizing_graph.pos = [new_x, new_y]

  const graph = g_resizing_graph.graph
  const post_data =
    'context=' +
    encodeURIComponent(JSON.stringify(graph.ajax_context)) +
    '&resize_x=' +
    delta_x +
    '&resize_y=' +
    delta_y

  start_graph_update(graph['canvas_obj'], post_data)
  return prevent_default_events(event)
}

// Get the mouse position of an event in coords of the
// shown time/value system. Return null if the coords
// lie outside.
function graph_get_mouse_position(event: MouseEvent, graph: GraphArtwork): null | [number, number] {
  const time = graph_get_click_time(event, graph)
  if (time < graph['time_axis']['range'][0] || time > graph['time_axis']['range'][1]) return null // out of range

  const value = graph_get_click_value(event, graph)
  if (value < graph['vertical_axis']['range'][0] || value > graph['vertical_axis']['range'][1])
    return null // out of range

  return [time, value]
}

function graph_mouse_down(event: Event, graph: GraphArtwork) {
  const pos = graph_get_mouse_position(event as MouseEvent, graph)
  if (!pos) return

  // Store information needed for update globally
  g_dragging_graph = {
    pos: pos,
    graph: graph
  }
  g_graph_update_in_process = false

  return prevent_default_events(event)
}

function has_mouse_moved(pos1: [number, number], pos2: [number, number] | null) {
  if (pos2 === null) {
    return true // assume mouse was moved when pos2 is outside of graph
  }
  return Math.abs(pos1[0] - pos2[0]) !== 0
}

function global_graph_mouse_up(event: Event) {
  let graph_id, graph
  if (g_dragging_graph) {
    graph = g_dragging_graph.graph
    const pos = graph_get_mouse_position(event as MouseEvent, graph)
    if (pos) {
      graph_id = graph['id']

      // When graph has not been dragged, the user did a simple click
      // Fire the graphs click action or, by default, positions the pin
      if (!has_mouse_moved(g_dragging_graph.pos, pos)) {
        handle_graph_clicked(graph)
        set_pin_position(event, graph, pos[0])
      }

      if (graph.render_config.interaction) sync_all_graph_timeranges(graph_id)
    }
  } else if (!g_resizing_graph) {
    const target = event!.target as HTMLElement
    if (target.tagName == 'TH' && has_class(target, 'scalar') && has_class(target, 'inactive')) {
      // Click on inactive scalar title: Change graph consolidation function to this one
      graph_id = get_graph_id_of_dom_node(target)
      if (graph_id) {
        graph = g_graphs[graph_id]

        let consolidation_function = ''
        if (has_class(target, 'min')) consolidation_function = 'min'
        else if (has_class(target, 'max')) consolidation_function = 'max'
        else consolidation_function = 'average'

        handle_graph_clicked(graph)
        set_consolidation_function(event, graph, consolidation_function)
      }
    } else if (target.tagName != 'IMG' && target.tagName != 'A') {
      graph_id = get_graph_id_of_dom_node(target)
      if (graph_id) {
        graph = g_graphs[graph_id]

        // clicked out of graphical area but on graph: remove the pin
        handle_graph_clicked(graph)
        remove_pin(event, graph)
      }
    }
  }

  g_dragging_graph = null
  g_resizing_graph = null
  g_graph_update_in_process = false
  return true
}

function handle_graph_clicked(graph: GraphArtwork) {
  if (graph.render_config.onclick) {
    /* eslint-disable-next-line no-eval -- Highlight existing violations CMK-17846 */
    eval(graph.render_config.onclick)
  }
}

function set_consolidation_function(
  event: Event,
  graph: GraphArtwork,
  consolidation_function: string
) {
  if (graph.render_config.interaction) {
    update_graph(event, graph, 0.0, null, null, null, null, consolidation_function)
    sync_all_graph_timeranges(graph.id!)
  }
}

function remove_pin(event: Event, graph: GraphArtwork) {
  // Only try to remove the pin when there is currently one
  if (graph.render_config.interaction && graph.render_config.show_pin && graph.pin_time !== null) {
    set_pin_position(event, graph, -1)
    sync_all_graph_timeranges(graph.id!)
  }
}

function set_pin_position(event: Event, graph: GraphArtwork, timestamp: number): boolean | void {
  if (graph.render_config.interaction && graph.render_config.show_pin)
    return update_graph(event, graph, 0.0, null, null, null, Math.trunc(timestamp), null)
}

// move is used for dragging and also for resizing
function graph_mouse_move(event: MouseEvent, graph: GraphArtwork) {
  if (!graph.render_config.interaction) return // don't do anything when this graph is not allowed to set the pin

  if (g_graph_update_in_process || g_graph_in_cooldown_period) return false

  if (g_dragging_graph == null || g_dragging_graph.graph.id != graph.id) return false // Not dragging or dragging other graph

  // Compute new time range
  const time_shift = g_dragging_graph.pos[0] - graph_get_click_time(event, graph)

  // Compute vertical zoom
  const value = graph_get_click_value(event, graph)
  let vertical_zoom: null | number = value / g_dragging_graph.pos[1]
  if (vertical_zoom <= 0) vertical_zoom = null // No mirroring, no zero range

  update_graph(event, graph, time_shift, null, null, vertical_zoom, null, null)

  return prevent_default_events(event)
}

function update_mouse_hovering(event: Event) {
  const canvas = mouse_hovering_canvas_graph_area(event as MouseEvent)
  remove_all_mouse_indicators()
  if (!canvas) {
    remove_all_graph_hover_popups()
    return
  }

  const graph_node = get_graph_graph_node(canvas)!
  const graph_id = get_graph_id_of_dom_node(graph_node)!
  const graph = g_graphs[graph_id]

  add()

  if (!graph.render_config.interaction) return // don't do anything when this graph is not allowed to set the pin

  const canvas_rect = canvas.getBoundingClientRect()
  update_mouse_indicator(
    canvas,
    graph,
    graph_node,
    (event as MouseEvent).clientX + canvas.offsetLeft - canvas_rect.left
  )
  update_graph_hover_popup(event, graph)
}

function mouse_hovering_canvas_graph_area(event: MouseEvent | undefined) {
  if (!event) throw new Error(`Expected event, got ${event} instead`)
  const obj = event.target as HTMLElement
  if (!obj) return null

  const graph_id = get_graph_id_of_dom_node(obj)
  if (!graph_id) return null

  const graph = g_graphs[graph_id]
  const canvas = graph['canvas_obj']!
  const canvas_rect = canvas.getBoundingClientRect()

  if (
    event.clientX < canvas_rect.left ||
    event.clientX > canvas_rect.right ||
    event.clientY < canvas_rect.top ||
    event.clientY > canvas_rect.bottom
  )
    return null // is not over canvas at all

  // Out of area on the left?
  const v_axis_width = to_display_coord(graph_vertical_axis_width(graph))
  const left_of_area = canvas_rect.left + v_axis_width + 4 // 4 is padding of graph container
  if (event.clientX < left_of_area) return null

  // Out of area on bottom?
  const bottom_border = to_display_coord(graph_bottom_border(graph))
  const bottom_of_area = canvas_rect.bottom - bottom_border
  if (event.clientY > bottom_of_area) return null

  return canvas
}

function update_mouse_indicator(
  canvas: HTMLCanvasElement,
  graph: GraphArtwork,
  graph_node: HTMLElement,
  x: number
) {
  const indicator = document.createElement('div')
  add_class(indicator, 'indicator')
  graph_node.appendChild(indicator)

  indicator.style.left = x + 'px'
  indicator.style.top = canvas.offsetTop + 'px'
  indicator.style.height = canvas.clientHeight - to_display_coord(graph_bottom_border(graph)) + 'px'
  indicator.style.pointerEvents = 'none'
}

function remove_all_mouse_indicators() {
  const indicators = document.getElementsByClassName('indicator')
  for (let i = 0, len = indicators.length; i < len; i++) {
    // @ts-ignore
    indicators[i].parentNode.removeChild(indicators[i])
  }
}

function graph_mouse_wheel(event: Event, graph: GraphArtwork) {
  if (!graph.render_config.interaction) return // don't do anything when this graph is not allowed to set the pin

  if (g_graph_update_in_process) return prevent_default_events(event)

  const time_zoom_center = graph_get_click_time(event as MouseEvent, graph)
  const delta = wheel_event_delta(event)

  let zoom: null | number = null
  if (delta > 0) {
    zoom = 1.1
  } else {
    // Do not zoom further in if we already display only 10 points or less
    const curves = graph['curves']
    if (curves.length == 0) return true
    const curve = curves[0]
    const points = curve['points']
    if (points.length <= 10) return true

    zoom = 1 / 1.1
  }

  if (!update_graph(event, graph, 0.0, zoom, time_zoom_center, null, null, null)) return false

  /* Also zoom all other graphs on the page */
  const graph_id = graph.id!
  if (g_graph_wheel_timeout) clearTimeout(g_graph_wheel_timeout)
  g_graph_wheel_timeout = window.setTimeout(function () {
    sync_all_graph_timeranges(graph_id)
  }, 500)

  return prevent_default_events(event)
}

function graph_get_click_time(event: MouseEvent, graph: GraphArtwork) {
  const canvas = event.target as HTMLCanvasElement

  // Get X position of mouse click, converted to canvas pixels
  const x = (get_event_offset_x(event) * canvas.width) / canvas.clientWidth

  // Convert this to a time value and check if its within the visible range
  const t_offset = (x - graph['time_origin']!) / graph['time_axis']['pixels_per_second']
  return graph['time_axis']['range'][0] + t_offset
}

function graph_get_click_value(event: MouseEvent, graph: GraphArtwork) {
  const canvas = event.target as HTMLCanvasElement

  // Get Y position of mouse click, converted to canvas pixels
  const y = (get_event_offset_y(event) * canvas.height) / canvas.clientHeight

  // Convert this to a vertical value and check if its within the visible range
  const v_offset = -(y - graph['vertical_origin']!) / graph['vertical_axis']['pixels_per_unit']
  return graph['vertical_axis']['range'][0] + v_offset
}

function get_event_offset_x(event: MouseEvent) {
  //@ts-ignore
  return event.offsetX == undefined ? event.layerX : event.offsetX
}

function get_event_offset_y(event: MouseEvent) {
  //https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent/layerY
  //@ts-ignore
  return event.offsetY == undefined ? event.layerY : event.offsetY
}

//#.
//#   .-Graph hover--------------------------------------------------------.
//#   |        ____                 _       _                              |
//#   |       / ___|_ __ __ _ _ __ | |__   | |__   _____   _____ _ __      |
//#   |      | |  _| '__/ _` | '_ \| '_ \  | '_ \ / _ \ \ / / _ \ '__|     |
//#   |      | |_| | | | (_| | |_) | | | | | | | | (_) \ V /  __/ |        |
//#   |       \____|_|  \__,_| .__/|_| |_| |_| |_|\___/ \_/ \___|_|        |
//#   |                      |_|                                           |
//#   '--------------------------------------------------------------------'

interface GraphHover {
  rendered_hover_time: string
  curve_values: CurveValues[]
}

function update_graph_hover_popup(event: Event, graph: GraphArtwork): boolean | void {
  if (g_graph_update_in_process || g_graph_in_cooldown_period) return prevent_default_events(event)

  const hover_timestamp = graph_get_click_time(event as MouseEvent, graph)

  if (!hover_timestamp) return prevent_default_events(event)

  if (
    hover_timestamp < graph['time_axis']['range'][0] ||
    hover_timestamp > graph['time_axis']['range'][1]
  )
    return prevent_default_events(event)

  const post_data =
    'context=' +
    encodeURIComponent(JSON.stringify(graph.ajax_context)) +
    '&hover_time=' +
    encodeURIComponent(Math.trunc(hover_timestamp))

  g_graph_update_in_process = true
  set_graph_update_cooldown()

  call_ajax('ajax_graph_hover.py', {
    method: 'POST',
    response_handler: handle_graph_hover_popup_update,
    handler_data: {
      graph: graph,
      event: event
    },
    post_data: post_data
  })
}

function handle_graph_hover_popup_update(
  handler_data: {
    graph: GraphArtwork
    event: Event
  },
  ajax_response: string
) {
  let popup_data: GraphHover
  try {
    popup_data = JSON.parse(ajax_response)
  } catch (e) {
    console.log(e)
    console.error('Failed to parse graph hover update response: ' + ajax_response)
    g_graph_update_in_process = false
    return
  }

  render_graph_hover_popup(handler_data.graph, handler_data.event, popup_data)

  //render_graph_and_subgraphs(graph);
  g_graph_update_in_process = false
}

interface CurveValues {
  color: string
  rendered_value: [number, string]
  title: string
}

interface PopupData {
  curve_values: CurveValues[]
  rendered_hover_time: string
}

// Structure of popup_data:
// {
//    "curve_values": [
//        {
//            "color": "#00d1ff",
//            "rendered_value": [0.5985, "0.599"],
//            "title": "CPU load average of last minute"
//        },
//        {
//            "color": "#2c5766",
//            "rendered_value": [0.538, "0.538"],
//            "title": "CPU load average of last 15 minutes"
//        }
//     ],
//     "rendered_hover_time": "2018-09-26 16:34:54"
// }
function render_graph_hover_popup(_graph: GraphArtwork, event: Event, popup_data: PopupData) {
  const wrapper = document.createElement('div')

  const popup_container = document.createElement('div')
  add_class(popup_container, 'graph_hover_popup')
  wrapper.appendChild(popup_container)

  const time = document.createElement('div')
  add_class(time, 'time')
  time.innerText = popup_data.rendered_hover_time
  popup_container.appendChild(time)

  const entries = document.createElement('table')
  add_class(entries, 'entries')
  popup_container.appendChild(entries)

  popup_data.curve_values.forEach((curve) => {
    const row = entries.insertRow()
    const title = row.insertCell(0)
    const color = document.createElement('div')
    add_class(color, 'color')
    color.style.backgroundColor = hex_to_rgba(curve.color + '4c')
    color.style.borderColor = curve.color
    title.appendChild(color)
    title.appendChild(document.createTextNode(curve.title + ': '))

    const value = row.insertCell(1)
    add_class(value, 'value')
    value.innerText = curve.rendered_value[1]
  })

  update_content(wrapper.innerHTML, event as MouseEvent)
}

// Hide the tooltips that show the metric values at the position of the pointer
function remove_all_graph_hover_popups() {
  for (const menu of document.getElementsByClassName('hover_menu')) {
    const graph_container = menu.getElementsByClassName('graph_hover_popup')
    if (graph_container.length > 0) {
      hide()
    }
  }
}

//#.
//#   .-Graph-Update-------------------------------------------------------.
//#   |   ____                 _           _   _           _       _       |
//#   |  / ___|_ __ __ _ _ __ | |__       | | | |_ __   __| | __ _| |_ ___ |
//#   | | |  _| '__/ _` | '_ \| '_ \ _____| | | | '_ \ / _` |/ _` | __/ _ \|
//#   | | |_| | | | (_| | |_) | | | |_____| |_| | |_) | (_| | (_| | ||  __/|
//#   |  \____|_|  \__,_| .__/|_| |_|      \___/| .__/ \__,_|\__,_|\__\___||
//#   |                 |_|                     |_|                        |
//#   +--------------------------------------------------------------------+
//#   | Handles re-rendering of graphs after user actions                  |
//#   '--------------------------------------------------------------------'

// TODO: Refactor the arguments to use something like ajax.call_ajax(). Makes things much clearer.
function update_graph(
  event: Event,
  graph: GraphArtwork,
  time_shift: number,
  time_zoom: number | null,
  time_zoom_center: number | null,
  vertical_zoom: number | null,
  pin_timestamp: number | null,
  consolidation_function: null | string
) {
  const canvas = graph['canvas_obj']

  let start_time: number
  let end_time: number

  // Time zoom
  if (time_zoom != null) {
    if (time_zoom_center === null) {
      throw new Error("time_zoom_center shouldn't be null!")
    }
    // The requested start/end time can differ from the real because
    // RRDTool align the times as it needs. The graph always is align
    // to the RRDTool data, but the zooming into small time intervals
    // does not work correctly if we do not base this on the requested start_time.
    start_time = time_zoom_center - (time_zoom_center - graph['requested_start_time']) * time_zoom
    end_time = time_zoom_center + (graph['requested_end_time'] - time_zoom_center) * time_zoom

    // Sanity check
    if (end_time < start_time) {
      end_time = start_time + 60
      start_time -= 60
    }

    // Do not allow less than 120 secs.
    const range = end_time - start_time
    if (range < 120) {
      const diff = 120 - range
      start_time -= ((time_zoom_center - start_time) / 120) * diff
      end_time += ((end_time - time_zoom_center) / 120) * diff
    }
  }

  // Time shift
  else {
    start_time = graph['start_time'] + time_shift
    end_time = graph['end_time'] + time_shift
  }

  // Check for range
  if (
    start_time < 0 ||
    end_time < 0 ||
    start_time > 2147483646 ||
    end_time > 2147483646 ||
    start_time > end_time
  ) {
    return true
  }

  // Vertical zoom
  let range_from: null | number = null
  let range_to: null | number = null
  if (vertical_zoom != null) {
    const old_range_from = graph['vertical_axis']['range'][0]
    const old_range_to = graph['vertical_axis']['range'][1]
    range_from = old_range_from / vertical_zoom
    range_to = old_range_to / vertical_zoom
  } else if (graph['requested_vrange'] != null) {
    range_from = graph['requested_vrange'][0]
    range_to = graph['requested_vrange'][1]
  }

  // Recompute step
  const step = (end_time - start_time) / canvas!.width / 2

  // wenn er einmal grob wurde, nie wieder fein wird, auch wenn man in
  // einen Bereich draggt, der wieder fein vorhanden wäre? Evtl. müssen
  // wir den Wunsch-Step neu berechnen. Oder sicher speichern, also
  // den ursprügnlichen Wunsch-Step anders als den vom RRD zurückgegebene.

  let post_data =
    'context=' +
    encodeURIComponent(JSON.stringify(graph.ajax_context)) +
    '&start_time=' +
    encodeURIComponent(start_time) +
    '&end_time=' +
    encodeURIComponent(end_time) +
    '&step=' +
    encodeURIComponent(step)

  if (range_from != null) {
    post_data +=
      '&range_from=' +
      encodeURIComponent(range_from) +
      '&range_to=' +
      encodeURIComponent(String(range_to))
  }

  if (pin_timestamp != null) {
    post_data += '&pin=' + encodeURIComponent(pin_timestamp)
  }

  if (consolidation_function != null) {
    post_data += '&consolidation_function=' + encodeURIComponent(consolidation_function)
  }

  if (g_graph_update_in_process) return prevent_default_events(event)

  start_graph_update(canvas!, post_data)
  return true
}

function start_graph_update(canvas: HTMLCanvasElement, post_data: string) {
  g_graph_update_in_process = true

  set_graph_update_cooldown()
  pause(g_page_update_delay)

  call_ajax('ajax_graph.py', {
    method: 'POST',
    //@ts-ignore
    response_handler: handle_graph_update,
    handler_data: get_graph_container(canvas),
    post_data: post_data
  })
}

function set_graph_update_cooldown() {
  g_graph_in_cooldown_period = true
  setTimeout(function () {
    g_graph_in_cooldown_period = false
  }, 100)
}

function handle_graph_update(graph_container: HTMLElement, ajax_response: string) {
  let response: AjaxGraph
  try {
    response = JSON.parse(ajax_response)
  } catch (e) {
    console.log(e)
    console.error('Failed to parse graph update response: ' + ajax_response)
    return
  }
  // Structure of response:
  // {
  //     "html" : html_code,
  //     "graph" : graph_artwork,
  //     "context" : {
  //         "graph_id"       : context["graph_id"],
  //         "definition"     : graph_recipe,
  //         "data_range"     : graph_data_range,
  //         "render_config"  : graph_render_config,
  // }
  const graph_id = response.context.graph_id
  const graph: GraphArtwork = response.graph
  graph['id'] = graph_id
  graph['ajax_context'] = response.context
  graph['render_config'] = graph['ajax_context']['render_config']
  g_graphs[graph_id] = graph

  // replace eventual references
  if (g_dragging_graph && g_dragging_graph.graph.id == graph.id) g_dragging_graph.graph = graph
  if (g_resizing_graph && g_resizing_graph.graph.id == graph.id) g_resizing_graph.graph = graph

  /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
  graph_container.innerHTML = response['html']

  render_graph_and_subgraphs(graph)
  g_graph_update_in_process = false
}

// re-render the given graph and check whether or not there are subgraphs
// which need to be re-rendered too.
function render_graph_and_subgraphs(graph: GraphArtwork) {
  render_graph(graph)

  for (const graph_id in g_graphs) {
    if (graph_id != graph.id && graph_id.substr(0, graph.id!.length) == graph.id) {
      render_graph(g_graphs[graph_id])
    }
  }
}

// Is called on the graph overview page when clicking on a timerange
// graph to change the timerange of the main graphs.
export function change_graph_timerange(graph: GraphArtwork, duration: number) {
  // Find the main graph by DOM tree:
  // <div class=graph_with_timeranges><div container of maingraph></td><table><tr><td>...myself
  const maingraph_container = get_main_graph_container(graph['canvas_obj'])

  const main_graph_id = maingraph_container.id
  const main_graph = g_graphs[main_graph_id]

  const now = Math.floor(new Date().getTime() / 1000)

  main_graph.start_time = now - duration
  main_graph.end_time = now

  pause(g_page_update_delay)
  sync_all_graph_timeranges(main_graph_id, false)
}

function update_pdf_export_link_timerange(start_time: number, end_time: number) {
  const context_buttons = document.getElementsByClassName('context_pdf_export')
  for (let i = 0; i < context_buttons.length; i++) {
    const context_button = context_buttons[i]
    if (context_button != undefined) {
      const link = context_button.getElementsByTagName('a')[0]
      link.href = makeuri({ start_time: start_time, end_time: end_time }, link.href)
    }
  }
}

let g_timerange_update_queue: [string, number, number][] = []

// Syncs all graphs on this page to the same time range as the selected graph.
// Be aware: set_graph_timerange triggers an AJAX request. Most browsers have
// a limit on the concurrent AJAX requests, so we need to slice the requests.
function sync_all_graph_timeranges(graph_id: string, skip_origin: boolean | undefined = undefined) {
  if (skip_origin === undefined) skip_origin = true

  g_timerange_update_queue = [] // abort all pending requests

  const graph = g_graphs[graph_id]
  for (const name in g_graphs) {
    // only look for the other graphs. Don't update graphs having fixed
    // time ranges, like the timerange chooser graphs on the overview page
    if ((!skip_origin || name != graph_id) && !g_graphs[name].render_config.fixed_timerange) {
      g_timerange_update_queue.push([name, graph.start_time, graph.end_time])
    }
  }

  update_delayed_graphs_timerange(graph.start_time, graph.end_time)
  update_pdf_export_link_timerange(graph.start_time, graph.end_time)

  // Kick off 4 graph timerange updaters (related to the number of maximum
  // parallel AJAX request)
  for (let i = 0; i < 4; i++) update_next_graph_timerange()
}

function update_next_graph_timerange() {
  const job = g_timerange_update_queue.pop()
  if (job) set_graph_timerange(job[0], job[1], job[2])
}

function set_graph_timerange(graph_id: string, start_time: number, end_time: number) {
  const graph = g_graphs[graph_id]
  const canvas = graph['canvas_obj']
  if (canvas) {
    const step = (end_time - start_time) / canvas.width / 2

    // wenn er einmal grob wurde, nie wieder fein wird, auch wenn man in
    // einen Bereich draggt, der wieder fein vorhanden wäre? Evtl. müssen
    // wir den Wunsch-Step neu berechnen. Oder sicher speichern, also
    // den ursprügnlichen Wunsch-Step anders als den vom RRD zurückgegebene.

    const post_data =
      'context=' +
      encodeURIComponent(JSON.stringify(graph.ajax_context)) +
      '&start_time=' +
      encodeURIComponent(start_time) +
      '&end_time=' +
      encodeURIComponent(end_time) +
      '&step=' +
      encodeURIComponent(step)

    call_ajax('ajax_graph.py', {
      method: 'POST',
      post_data: post_data,
      //this is related to the third argument of the function, which I think is never used in ajax.ts
      response_handler: handle_graph_timerange_update,
      handler_data: get_graph_container(canvas)
    })
  }
}

// First updates the current graph and then continues with the next graph
function handle_graph_timerange_update(graph_container: HTMLElement, ajax_response: string) {
  handle_graph_update(graph_container, ajax_response)
  update_next_graph_timerange()
}

interface Attribute {
  name: string
  value: string
  type: string
}

export function showAttributes(
  event: MouseEvent,
  title: string,
  headers: string[],
  attributes: Attribute[]
) {
  const wrapper = document.createElement('div')

  const wrapperInner = document.createElement('div')
  wrapperInner.className = 'metric_attributes'

  const wrapperTitle = document.createElement('div')
  wrapperTitle.innerHTML = title

  const wrapperTable = document.createElement('div')
  const table = document.createElement('table')
  const headerRow = document.createElement('tr')
  headers.forEach((header) => {
    const th = document.createElement('th')
    th.textContent = header
    headerRow.appendChild(th)
  })
  table.appendChild(headerRow)
  attributes.forEach((attribute) => {
    const row = table.insertRow()
    const name = row.insertCell(0)
    name.appendChild(document.createTextNode(attribute.name))
    const value = row.insertCell(1)
    value.appendChild(document.createTextNode(attribute.value))
    const type = row.insertCell(2)
    type.appendChild(document.createTextNode(attribute.type))
  })
  wrapperTable.append(table)

  wrapperInner.append(wrapperTitle, wrapperTable)
  wrapper.append(wrapperInner)

  show(event, wrapper.innerHTML)
}

export function hideAttributes() {
  hide()
}
