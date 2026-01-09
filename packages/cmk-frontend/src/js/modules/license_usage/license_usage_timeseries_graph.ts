/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ScaleTime, Selection } from 'd3'
import {
  ascending,
  axisBottom,
  axisLeft,
  curveStepAfter,
  pointer as d3_pointer,
  format,
  line,
  max,
  min,
  scaleLinear,
  scaleTime,
  select,
  timeMonth
} from 'd3'

// From cmk/utils/licensing/export.py:

interface RawSubscriptionDetailsForAggregation {
  start: number | null
  end: number | null
  limit: 'unlimited' | number | null
}

interface RawMonthlyServiceAverage {
  sample_time: number
  num_services: number
}

interface RawMonthlyServiceAggregation {
  subscription_details: RawSubscriptionDetailsForAggregation
  daily_services: RawMonthlyServiceAverage[]
  monthly_service_averages: RawMonthlyServiceAverage[]
  last_service_report: RawMonthlyServiceAverage | null
  highest_service_report: RawMonthlyServiceAverage | null
  subscription_exceeded_first: RawMonthlyServiceAverage | null
}

interface MonthlyServiceAverage {
  sample_date: Date
  num_services: number
}

interface BarData {
  class: string
  sample_date: Date
  num_services: number
}

interface BarDataExtended {
  class: string
  sample_date: Date
  num_services: number
  num_bars: number
  index: number
}

interface LegendRowData {
  class_legend_line: string
  title_line: string
  class_legend_square: string
  title_square: string
  value_square: RawMonthlyServiceAverage | null
}

function ts_to_date(unix_timestamp: number) {
  return new Date(unix_timestamp * 1000)
}

function compute_x_domain(
  subscription_start: number | null,
  subscription_end: number | null,
  raw_daily_services: RawMonthlyServiceAverage[]
) {
  if (subscription_start !== null && subscription_end !== null) {
    const dummy_seconds = 10 * 24 * 60 * 60
    return [
      ts_to_date(subscription_start - dummy_seconds),
      ts_to_date(subscription_end + dummy_seconds)
    ]
  }
  if (raw_daily_services.length > 0) {
    const min_daily_service = min(raw_daily_services, function (d) {
      return d.sample_time
    })
    const max_daily_service = max(raw_daily_services, function (d) {
      return d.sample_time
    })
    if (min_daily_service !== undefined && max_daily_service !== undefined) {
      return [ts_to_date(min_daily_service), ts_to_date(max_daily_service)]
    }
  }
  return null
}

function compute_y_domain_max(
  subscription_limit: 'unlimited' | number | null,
  raw_daily_services: RawMonthlyServiceAverage[],
  y_domain_max: number
) {
  let y_domain_max_values = []
  if (subscription_limit !== 'unlimited' && subscription_limit !== null) {
    y_domain_max_values.push(subscription_limit)
  }
  if (raw_daily_services.length > 0) {
    y_domain_max_values = y_domain_max_values.concat(
      raw_daily_services.map(function (d) {
        return d.num_services
      })
    )
  }
  if (y_domain_max_values.length > 0) {
    const y_domain_max = max(y_domain_max_values)
    if (y_domain_max) {
      let factor
      if (y_domain_max > 10000) {
        factor = 10000
      } else if (y_domain_max > 1000) {
        factor = 1000
      } else if (y_domain_max > 100) {
        factor = 100
      } else if (y_domain_max > 10) {
        factor = 10
      } else {
        factor = 1
      }
      return Math.ceil((1.1 * y_domain_max) / factor) * factor
    }
  }
  return y_domain_max
}

function compute_daily_services(
  raw_daily_services: RawMonthlyServiceAverage[],
  x_domain_min: Date,
  x_domain_max: Date
) {
  const daily_services: MonthlyServiceAverage[] = []
  raw_daily_services
    .sort(function (a, b) {
      return ascending(a.sample_time, b.sample_time)
    })
    .forEach(function (d) {
      daily_services.push({
        sample_date: ts_to_date(d.sample_time),
        num_services: d.num_services
      })
    })
  return daily_services.filter(function (d) {
    return x_domain_min <= d.sample_date && d.sample_date <= x_domain_max
  })
}

function compute_monthly_service_averages(
  raw_monthly_service_averages: RawMonthlyServiceAverage[]
) {
  const monthly_service_averages: MonthlyServiceAverage[] = []
  if (raw_monthly_service_averages.length > 0) {
    raw_monthly_service_averages.forEach(function (d) {
      monthly_service_averages.push({
        sample_date: ts_to_date(d.sample_time),
        num_services: d.num_services
      })
    })
    // add last sample with month offset 1 in order to draw the last line
    const last_sample = raw_monthly_service_averages[raw_monthly_service_averages.length - 1]
    monthly_service_averages.push({
      sample_date: timeMonth.offset(ts_to_date(last_sample.sample_time), 1),
      num_services: last_sample.num_services
    })
  }
  return monthly_service_averages
}

function compute_bar_data(
  highest_service_report: RawMonthlyServiceAverage | null,
  subscription_exceeded_first: RawMonthlyServiceAverage | null,
  last_service_report: RawMonthlyServiceAverage | null
) {
  // Due to this calculcation of bar_dates we adapt the bar sizes:
  // It's possible that all three bars or at least two bars may be
  // placed in the same month.
  const bar_data: BarData[] = []
  if (highest_service_report) {
    bar_data.push({
      class: 'legend-highest-usage',
      sample_date: ts_to_date(highest_service_report.sample_time),
      num_services: highest_service_report.num_services
    })
  }
  if (subscription_exceeded_first) {
    bar_data.push({
      class: 'legend-first-above-subscription',
      sample_date: ts_to_date(subscription_exceeded_first.sample_time),
      num_services: subscription_exceeded_first.num_services
    })
  }
  if (last_service_report) {
    bar_data.push({
      class: 'legend-current-usage',
      sample_date: ts_to_date(last_service_report.sample_time),
      num_services: last_service_report.num_services
    })
  }
  const bar_lengths: { [key: string]: BarData[] } = {}
  bar_data.forEach(function (d) {
    const key = d.sample_date.getFullYear() + '-' + d.sample_date.getMonth()
    if (!(key in bar_lengths)) {
      bar_lengths[key] = []
    }
    bar_lengths[key].push(d)
  })
  const bar_data_extended: BarDataExtended[] = []
  bar_data.forEach(function (d) {
    const key = d.sample_date.getFullYear() + '-' + d.sample_date.getMonth()
    bar_data_extended.push({
      class: d.class,
      sample_date: d.sample_date,
      num_services: d.num_services,
      num_bars: bar_lengths[key].length,
      index: bar_lengths[key].indexOf(d)
    })
  })
  // Order will be "Current", "First", "Highest"
  bar_data_extended.reverse()
  return bar_data_extended
}

// Three bars:
//   |###|///|@@@|
//   |###|///|@@@|
//   |###|///|@@@|
//   |###|///|@@@|
//   |###|///|@@@|
// --|---'---'---|--
//  Jan         Feb

// Two and one bars:
//   |#####|/////|           |@@@@@@@@@@@|
//   |#####|/////|           |@@@@@@@@@@@|
//   |#####|/////|           |@@@@@@@@@@@|
//   |#####|/////|           |@@@@@@@@@@@|
//   |#####|/////|           |@@@@@@@@@@@|
// --|-----'-----|-----------|-----------|--
//  Jan         Feb         Mar         Apr

function get_bar_size(x_range: ScaleTime<number, number, any>, bar_data_extended: BarDataExtended) {
  return (
    (x_range(timeMonth.offset(bar_data_extended.sample_date, 1)) -
      x_range(bar_data_extended.sample_date)) /
    bar_data_extended.num_bars
  )
}

function get_tooltip_date_info(x_coord_date: Date) {
  return (
    x_coord_date.getFullYear() + '-' + (x_coord_date.getMonth() + 1) + '-' + x_coord_date.getDate()
  )
}

function get_tooltip_num_service_info(
  x_coord_date: Date,
  daily_services: MonthlyServiceAverage[],
  tooltip_title: string
) {
  const the_year = x_coord_date.getFullYear(),
    the_month = x_coord_date.getMonth(),
    the_day = x_coord_date.getDate()

  let num_services_info = '-'
  for (let i = 0; i < daily_services.length; i++) {
    const daily_service = daily_services[i]
    const sample_date = daily_service.sample_date
    if (
      sample_date.getFullYear() === the_year &&
      sample_date.getMonth() === the_month &&
      sample_date.getDate() === the_day
    ) {
      num_services_info = format('~s')(Math.trunc(daily_service.num_services))
      break
    }
  }
  return tooltip_title + ': ' + num_services_info
}

function get_tooltip_average_info(
  x_coord_date: Date,
  monthly_service_averages: MonthlyServiceAverage[],
  tooltip_title: string
) {
  let average_info = '-'
  for (let i = 0; i < monthly_service_averages.length; i++) {
    const average = monthly_service_averages[i],
      offset = timeMonth.offset(average.sample_date, 1)
    if (average.sample_date <= x_coord_date && x_coord_date < offset) {
      average_info = format('~s')(Math.trunc(average.num_services))
      break
    }
  }
  return '&empty; ' + tooltip_title + ': ' + average_info
}

function get_tooltip_limit_info(
  x_coord_date: Date,
  subscription_start: number | null,
  subscription_end: number | null,
  subscription_limit: 'unlimited' | number | null,
  subscription_sizing_title: string,
  tooltip_title: string
) {
  if (subscription_limit === 'unlimited') {
    return subscription_sizing_title + ': Unlimited'
  }
  if (subscription_limit === null) {
    return subscription_sizing_title + ': -'
  }
  let limit_info = format('~s')(Math.trunc(subscription_limit)) + ' ' + tooltip_title
  if (subscription_start && subscription_end) {
    const x_coord_time = x_coord_date.getTime() / 1000
    if (x_coord_time < subscription_start || subscription_end < x_coord_time) {
      limit_info = '-'
    }
  }
  return subscription_sizing_title + ': ' + limit_info
}

function add_legend_row(
  table: Selection<HTMLTableElement, unknown, HTMLElement, unknown>,
  data: LegendRowData
) {
  const row = table.append('tr')
  row
    .append('td')
    .append('svg')
    .attr('height', 20)
    .attr('width', 20)
    .append('rect')
    .attr('class', data.class_legend_line)
    .attr('x', 0)
    .attr('y', 11)
    .attr('height', 3)
    .attr('width', 20)
  row.append('td').attr('class', 'legend-td-extra-space').text(data.title_line)

  row
    .append('td')
    .append('svg')
    .attr('height', 20)
    .attr('width', 20)
    .append('rect')
    .attr('class', data.class_legend_square)
    .attr('x', 0)
    .attr('y', 2)
    .attr('height', 20)
    .attr('width', 20)
  row.append('td').text(data.title_square + ':')

  let date_info = '-'
  if (data.value_square !== null) {
    const date = ts_to_date(data.value_square.sample_time)
    date_info = date.getFullYear() + '-' + (date.getMonth() + 1) + '-' + date.getDate()
  }
  row.append('td').text(date_info)
}

interface GraphConfig {
  y_domain_max: number
  width: number
  graph_title: string
  subscription_sizing_title: string
  subscription_sizing_line_class: string
  subscription_sizing_legend_class: string
  daily_title: string
  monthly_averages_title: string
  tooltip_title: string
  first_above_limit_title: string
}

function render_usage_graph(graph_config: GraphConfig, aggregation: RawMonthlyServiceAggregation) {
  const subscription_start = aggregation.subscription_details.start
  const subscription_end = aggregation.subscription_details.end
  const subscription_limit = aggregation.subscription_details.limit

  const x_domain = compute_x_domain(
    subscription_start,
    subscription_end,
    aggregation.daily_services
  )
  if (x_domain === null) {
    throw new Error('cannot render graph due to unknown time range')
    return
  }
  const y_domain_max = compute_y_domain_max(
    subscription_limit,
    aggregation.daily_services,
    graph_config.y_domain_max
  )

  // Prepare daily services
  const daily_services = compute_daily_services(
    aggregation.daily_services,
    x_domain[0],
    x_domain[1]
  )

  // Prepare monthly averages
  const monthly_service_averages = compute_monthly_service_averages(
    aggregation.monthly_service_averages
  )

  // Prepare bars
  const bar_data_extended = compute_bar_data(
    aggregation.highest_service_report,
    aggregation.subscription_exceeded_first,
    aggregation.last_service_report
  )

  // set the dimensions and margins of the graph
  const width = graph_config.width
  const height = 500
  const margin = { top: 60, right: 50, bottom: 20, left: 40 }
  const inner_width = width - margin.left - margin.right
  const inner_height = height - margin.top - margin.bottom

  const x_range = scaleTime().domain(x_domain).range([0, inner_width])
  const y_range = scaleLinear().domain([0, y_domain_max]).range([inner_height, 0])
  const x_axis = axisBottom(x_range).ticks(5)
  const y_axis_left = axisLeft(y_range).tickFormat(format('~s')).ticks(10)

  const line_daily_services = line<MonthlyServiceAverage>()
    .x(function (d) {
      return x_range(d.sample_date)
    })
    .y(function (d) {
      return y_range(d.num_services)
    })

  const line_monthly_average_services = line<MonthlyServiceAverage>()
    .curve(curveStepAfter)
    .x(function (d) {
      return x_range(d.sample_date)
    })
    .y(function (d) {
      return y_range(d.num_services)
    })

  const container = select('#detailed_timeline').append('div').attr('class', 'graph')
  const svg = container
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .append('g')
    .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')')

  svg
    .append('text')
    .attr('class', 'title')
    .attr('x', inner_width / 2)
    .attr('y', 0 - margin.top / 2)
    .attr('text-anchor', 'middle')
    .style('font-size', '18px')
    .style('font-weight', 'bold')
    .text(graph_config.graph_title)

  svg
    .append('g')
    .append('clipPath')
    .attr('id', 'clip')
    .append('rect')
    .attr('x', 0)
    .attr('y', 0)
    .attr('width', width)
    .attr('height', height)

  svg
    .append('g')
    .attr('class', 'x axis')
    .attr('transform', 'translate(0,' + inner_height + ')')
    .call(x_axis)

  svg.append('g').attr('class', 'y axis left').call(y_axis_left)

  svg
    .selectAll('.bar')
    .data(bar_data_extended)
    .enter()
    .append('g')
    .attr('class', function (d) {
      return 'bar ' + d.class
    })
    .append('rect')
    .attr('clip-path', 'url(#clip)')
    .attr('x', function (d) {
      return x_range(d.sample_date) + d.index * get_bar_size(x_range, d)
    })
    .attr('y', function (d) {
      return y_range(d.num_services)
    })
    .attr('width', function (d) {
      return get_bar_size(x_range, d)
    })
    .attr('height', function (d) {
      return inner_height - y_range(d.num_services)
    })

  svg
    .selectAll('.line-daily-services')
    .data([daily_services])
    .enter()
    .append('g')
    .attr('class', 'line-daily-services')
    .append('path')
    .attr('d', line_daily_services)

  svg
    .selectAll('.line-monthly-service-averages')
    .data([monthly_service_averages])
    .enter()
    .append('g')
    .attr('class', 'line-monthly-service-averages')
    .append('path')
    .attr('clip-path', 'url(#clip)')
    .attr('d', line_monthly_average_services)

  if (subscription_limit !== 'unlimited' && subscription_limit !== null) {
    let start
    let end
    if (subscription_start && subscription_end) {
      start = x_range(ts_to_date(subscription_start))
      end = x_range(ts_to_date(subscription_end))
    } else {
      start = 0
      end = inner_width
    }
    svg
      .append('g')
      .attr('class', graph_config.subscription_sizing_line_class)
      .append('line')
      .attr('x1', start)
      .attr('x2', end)
      .attr('y1', y_range(subscription_limit))
      .attr('y2', y_range(subscription_limit))
  }

  if (subscription_start && subscription_end) {
    const subscription_start_end = svg
      .selectAll('.subscription-start-end')
      .data([
        {
          x: x_range(ts_to_date(subscription_start)),
          title: 'Subscription start'
        },
        {
          x: x_range(ts_to_date(subscription_end)),
          title: 'Subscription end'
        }
      ])
      .enter()
      .append('g')
      .attr('class', 'subscription-start-end')

    subscription_start_end
      .append('line')
      .attr('class', 'line-subscription-start-end')
      .attr('x1', function (d) {
        return d.x
      })
      .attr('x2', function (d) {
        return d.x
      })
      .attr('y1', inner_height)
      .attr('y2', 0)

    subscription_start_end
      .append('text')
      .attr('class', 'title text-subscription-start-end')
      .attr('x', function (d) {
        return d.x
      })
      .attr('y', 0)
      .attr('dy', '-15')
      .text(function (d) {
        return d.title
      })
  }

  const tooltip = select('body').append('div').attr('class', 'tooltip license_usage')
  const pointer_events = svg.append('g').attr('class', 'pointer-over-effects')
  const h_line = pointer_events.append('path').attr('class', 'line-pointer')
  const v_line = pointer_events.append('path').attr('class', 'line-pointer')

  pointer_events
    .append('svg:rect')
    .attr('width', inner_width)
    .attr('height', inner_height)
    .attr('fill', 'none')
    .attr('pointer-events', 'all')
    .on('pointerout', function () {
      tooltip.classed('on', false)
      h_line.classed('on', false)
      v_line.classed('on', false)
    })
    .on('pointerover', function () {
      tooltip.classed('on', true)
      h_line.classed('on', true)
      v_line.classed('on', true)
    })
    .on('pointermove', function () {
      const pointer = d3_pointer(event)
      v_line.classed('on', true).attr('d', function () {
        let d = 'M' + pointer[0] + ',' + inner_height
        d += ' ' + pointer[0] + ',' + 0
        return d
      })
      h_line.classed('on', true).attr('d', function () {
        let d = 'M' + 0 + ',' + pointer[1]
        d += ' ' + inner_width + ',' + pointer[1]
        return d
      })

      const x_coord_date = x_range.invert(pointer[0])
      tooltip
        .classed('on', true)
        .style('top', (event as MouseEvent).pageY - 10 + 'px')
        .style('left', (event as MouseEvent).pageX + 10 + 'px')
        .html(
          'Date: ' +
            get_tooltip_date_info(x_coord_date) +
            '<br>' +
            get_tooltip_num_service_info(x_coord_date, daily_services, graph_config.tooltip_title) +
            '<br>' +
            get_tooltip_average_info(
              x_coord_date,
              monthly_service_averages,
              graph_config.tooltip_title
            ) +
            '<br>' +
            get_tooltip_limit_info(
              x_coord_date,
              subscription_start,
              subscription_end,
              subscription_limit,
              graph_config.subscription_sizing_title,
              graph_config.tooltip_title
            )
        )
    })

  const legend_table = container.append('table').attr('class', 'legend-table')

  add_legend_row(legend_table, {
    class_legend_line: graph_config.subscription_sizing_legend_class,
    title_line: graph_config.subscription_sizing_title,
    class_legend_square: 'legend-current-usage',
    title_square: 'Current monthly average usage',
    value_square: aggregation.last_service_report
  })

  add_legend_row(legend_table, {
    class_legend_line: 'legend-monthly-service-averages',
    title_line: graph_config.monthly_averages_title,
    class_legend_square: 'legend-first-above-subscription',
    title_square: graph_config.first_above_limit_title,
    value_square: aggregation.subscription_exceeded_first
  })

  add_legend_row(legend_table, {
    class_legend_line: 'legend-daily-services',
    title_line: graph_config.daily_title,
    class_legend_square: 'legend-highest-usage',
    title_square: 'Highest monthly average usage',
    value_square: aggregation.highest_service_report
  })
}

//// MAIN ////

export function render_services_usage_graph(
  num_graphs: number,
  services_aggregation: RawMonthlyServiceAggregation
) {
  render_usage_graph(
    {
      y_domain_max: 1000,
      width: Math.floor((0.9 * window.innerWidth) / num_graphs),
      graph_title: 'Checkmk',
      subscription_sizing_title: 'Subscription sizing',
      subscription_sizing_line_class: 'line-subscription-limit',
      subscription_sizing_legend_class: 'legend-subscription-limit',
      daily_title: 'Daily services',
      monthly_averages_title: 'Monthly service averages',
      tooltip_title: 'Services',
      first_above_limit_title: 'First monthly average usage above subscription limit'
    },
    services_aggregation
  )
}

export function render_tests_usage_graph(
  num_graphs: number,
  tests_aggregation: RawMonthlyServiceAggregation
) {
  render_usage_graph(
    {
      y_domain_max: 10,
      width: Math.floor((0.9 * window.innerWidth) / num_graphs),
      graph_title: 'Synthetic Monitoring',
      subscription_sizing_title: 'Subscription sizing',
      subscription_sizing_line_class: 'line-subscription-limit',
      subscription_sizing_legend_class: 'legend-subscription-limit',
      daily_title: 'Daily tests',
      monthly_averages_title: 'Monthly test averages',
      tooltip_title: 'Tests',
      first_above_limit_title: 'First monthly average usage above subscription limit'
    },
    tests_aggregation
  )
}

export function render_free_tests_usage_graph(
  num_graphs: number,
  tests_aggregation: RawMonthlyServiceAggregation
) {
  render_usage_graph(
    {
      y_domain_max: 10,
      width: Math.floor((0.9 * window.innerWidth) / num_graphs),
      graph_title: 'Synthetic Monitoring',
      subscription_sizing_title: 'Free tests',
      subscription_sizing_line_class: 'line-free-limit',
      subscription_sizing_legend_class: 'legend-free-limit',
      daily_title: 'Daily tests',
      monthly_averages_title: 'Monthly test averages',
      tooltip_title: 'Tests',
      first_above_limit_title: 'First monthly average usage above free limit'
    },
    tests_aggregation
  )
}

export function render_metric_series_usage_graph(
  num_graphs: number,
  metric_series_aggregation: RawMonthlyServiceAggregation
) {
  render_usage_graph(
    {
      y_domain_max: 1000,
      width: Math.floor((0.9 * window.innerWidth) / num_graphs),
      graph_title: 'Telemetry',
      subscription_sizing_title: 'Subscription sizing',
      subscription_sizing_line_class: 'line-subscription-limit',
      subscription_sizing_legend_class: 'legend-subscription-limit',
      daily_title: 'Daily active metric series',
      monthly_averages_title: 'Monthly active metric series averages',
      tooltip_title: 'Active Metric Series',
      first_above_limit_title: 'First monthly average usage above subscription limit'
    },
    metric_series_aggregation
  )
}

export function render_free_metric_series_usage_graph(
  num_graphs: number,
  metric_series_aggregation: RawMonthlyServiceAggregation
) {
  render_usage_graph(
    {
      y_domain_max: 1000,
      width: Math.floor((0.9 * window.innerWidth) / num_graphs),
      graph_title: 'Telemetry',
      subscription_sizing_title: 'Free metric series',
      subscription_sizing_line_class: 'line-free-limit',
      subscription_sizing_legend_class: 'legend-free-limit',
      daily_title: 'Daily active metric series',
      monthly_averages_title: 'Monthly active metric series averages',
      tooltip_title: 'Active Metric Series',
      first_above_limit_title: 'First monthly average usage above free limit'
    },
    metric_series_aggregation
  )
}
