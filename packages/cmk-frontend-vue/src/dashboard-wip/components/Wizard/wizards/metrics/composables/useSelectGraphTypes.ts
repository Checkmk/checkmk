/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import { ElementSelection } from '@/dashboard-wip/components/Wizard/types'

export enum MetricSelection {
  SINGLE_METRIC = 'SINGLE',
  COMBINED_GRAPH = 'COMBINED'
}

export enum Graph {
  SINGLE_GRAPH = 'single_timeseries',
  GAUGE = 'gauge',
  SINGLE_METRIC = 'single_metric',
  BARPLOT = 'barplot',
  SCATTERPLOT = 'average_scatterplot',
  TOP_LIST = 'top_list',
  PERFORMANCE_GRAPH = 'performance_graph',
  COMBINED_GRAPH = 'combined_graph',
  ANY_GRAPH = 'ANY_GRAPH'
}

const graphSelector = {
  [ElementSelection.SPECIFIC]: {
    //host
    [ElementSelection.SPECIFIC]: {
      //service
      [MetricSelection.SINGLE_METRIC]: [
        Graph.SINGLE_GRAPH,
        Graph.GAUGE,
        Graph.SINGLE_METRIC,
        Graph.BARPLOT,
        Graph.SCATTERPLOT,
        Graph.TOP_LIST,
        Graph.ANY_GRAPH
      ],

      [MetricSelection.COMBINED_GRAPH]: [Graph.PERFORMANCE_GRAPH, Graph.ANY_GRAPH]
    },

    [ElementSelection.MULTIPLE]: {
      //service
      [MetricSelection.SINGLE_METRIC]: [Graph.SCATTERPLOT, Graph.TOP_LIST],

      [MetricSelection.COMBINED_GRAPH]: [Graph.COMBINED_GRAPH, Graph.ANY_GRAPH]
    }
  },

  [ElementSelection.MULTIPLE]: {
    //host
    [ElementSelection.SPECIFIC]: {
      //service
      [MetricSelection.SINGLE_METRIC]: [Graph.BARPLOT, Graph.SCATTERPLOT, Graph.TOP_LIST],

      [MetricSelection.COMBINED_GRAPH]: [Graph.COMBINED_GRAPH, Graph.ANY_GRAPH]
    },

    [ElementSelection.MULTIPLE]: {
      //service
      [MetricSelection.SINGLE_METRIC]: [Graph.SCATTERPLOT, Graph.TOP_LIST],

      [MetricSelection.COMBINED_GRAPH]: [Graph.COMBINED_GRAPH, Graph.ANY_GRAPH]
    }
  }
}

type UseAvailableGraphs = Ref<Graph[]>

export const useSelectGraphTypes = (
  hostSelection: Ref<ElementSelection>,
  serviceSelection: Ref<ElementSelection>,
  metricSelection: Ref<MetricSelection>
): UseAvailableGraphs => {
  const availableGraphs = ref<Graph[]>([])

  watch(
    [hostSelection, serviceSelection, metricSelection],
    ([newHostSelection, newServiceSelection, newMetricSelection]) => {
      availableGraphs.value = [
        ...graphSelector[newHostSelection][newServiceSelection][newMetricSelection]
      ]
    },
    { deep: true, immediate: true }
  )

  return availableGraphs
}

export const getAvailableGraphs = (
  hostSelection: ElementSelection,
  serviceSelection: ElementSelection,
  metricSelection: MetricSelection
): Graph[] => {
  return [...graphSelector[hostSelection][serviceSelection][metricSelection]]
}

interface GetDefaultsFromGraph {
  hostSelection: ElementSelection
  serviceSelection: ElementSelection
  metricSelection: MetricSelection
}

export const getDefaultsFromGraph = (graph?: Graph | string): GetDefaultsFromGraph => {
  let hostSelection: ElementSelection = ElementSelection.SPECIFIC
  let serviceSelection: ElementSelection = ElementSelection.SPECIFIC
  let metricSelection: MetricSelection = MetricSelection.SINGLE_METRIC

  switch (graph) {
    case Graph.BARPLOT:
      hostSelection = ElementSelection.MULTIPLE
      break

    case Graph.SCATTERPLOT:
      hostSelection = ElementSelection.MULTIPLE
      serviceSelection = ElementSelection.MULTIPLE
      break

    case Graph.TOP_LIST:
      hostSelection = ElementSelection.MULTIPLE
      serviceSelection = ElementSelection.MULTIPLE
      break

    case Graph.PERFORMANCE_GRAPH:
      metricSelection = MetricSelection.COMBINED_GRAPH
      break

    case Graph.COMBINED_GRAPH:
      hostSelection = ElementSelection.MULTIPLE
      serviceSelection = ElementSelection.MULTIPLE
      metricSelection = MetricSelection.COMBINED_GRAPH
      break
  }

  return {
    hostSelection,
    serviceSelection,
    metricSelection
  }
}
