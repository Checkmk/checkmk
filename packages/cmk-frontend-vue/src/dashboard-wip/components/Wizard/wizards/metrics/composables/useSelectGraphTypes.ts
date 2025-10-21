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
  SINGLE_GRAPH = 'SINGLE_GRAPH',
  GAUGE = 'GAUGE',
  SINGLE_METRIC = 'SINGLE_METRIC',
  BARPLOT = 'BARPLOT',
  SCATTERPLOT = 'SCATTERPLOT',
  TOP_LIST = 'TOP_LIST',
  PERFORMANCE_GRAPH = 'PERFORMANCE_GRAPH',
  COMBINED_GRAPH = 'COMBINED_GRAPH',
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

      [MetricSelection.COMBINED_GRAPH]: [
        Graph.PERFORMANCE_GRAPH,
        Graph.COMBINED_GRAPH,
        Graph.ANY_GRAPH
      ]
    },

    [ElementSelection.MULTIPLE]: {
      //service
      [MetricSelection.SINGLE_METRIC]: [Graph.SCATTERPLOT, Graph.TOP_LIST],

      [MetricSelection.COMBINED_GRAPH]: [
        Graph.PERFORMANCE_GRAPH,
        Graph.COMBINED_GRAPH,
        Graph.ANY_GRAPH
      ]
    }
  },

  [ElementSelection.MULTIPLE]: {
    //host
    [ElementSelection.SPECIFIC]: {
      //service
      [MetricSelection.SINGLE_METRIC]: [Graph.BARPLOT, Graph.SCATTERPLOT, Graph.TOP_LIST],

      [MetricSelection.COMBINED_GRAPH]: [
        Graph.PERFORMANCE_GRAPH,
        Graph.COMBINED_GRAPH,
        Graph.ANY_GRAPH
      ]
    },

    [ElementSelection.MULTIPLE]: {
      //service
      [MetricSelection.SINGLE_METRIC]: [Graph.SCATTERPLOT, Graph.TOP_LIST],

      [MetricSelection.COMBINED_GRAPH]: [
        Graph.PERFORMANCE_GRAPH,
        Graph.COMBINED_GRAPH,
        Graph.ANY_GRAPH
      ]
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
