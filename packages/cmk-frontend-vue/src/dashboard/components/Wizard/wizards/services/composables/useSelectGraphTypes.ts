/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import { ElementSelection } from '@/dashboard/components/Wizard/types'
import { DashboardFeatures } from '@/dashboard/types/dashboard'

export enum Graph {
  SERVICE_STATE = 'service_state',
  SERVICE_STATE_SUMMARY = 'service_state_summary',
  SERVICE_STATS = 'service_stats'
}

const graphSelector = {
  //host
  [ElementSelection.SPECIFIC]: {
    //service
    [ElementSelection.SPECIFIC]: [
      Graph.SERVICE_STATE,
      Graph.SERVICE_STATE_SUMMARY,
      Graph.SERVICE_STATS
    ],
    [ElementSelection.MULTIPLE]: [Graph.SERVICE_STATE_SUMMARY, Graph.SERVICE_STATS]
  },

  //host
  [ElementSelection.MULTIPLE]: {
    //service
    [ElementSelection.SPECIFIC]: [Graph.SERVICE_STATE_SUMMARY, Graph.SERVICE_STATS],
    [ElementSelection.MULTIPLE]: [Graph.SERVICE_STATE_SUMMARY, Graph.SERVICE_STATS]
  }
}

type UseAvailableGraphs = Ref<Graph[]>

export const useSelectGraphTypes = (
  hostSelection: Ref<ElementSelection>,
  serviceSelection: Ref<ElementSelection>,
  availableFeatures: DashboardFeatures
): UseAvailableGraphs => {
  const availableGraphs = ref<Graph[]>([])

  watch(
    [hostSelection, serviceSelection],
    ([newHostSelection, newServiceSelection]) => {
      availableGraphs.value = getAvailableGraphs(
        newHostSelection,
        newServiceSelection,
        availableFeatures
      )
    },
    { deep: true, immediate: true }
  )

  return availableGraphs
}

export const getAvailableGraphs = (
  hostSelection: ElementSelection,
  serviceSelection: ElementSelection,
  availableFeatures: DashboardFeatures
): Graph[] => {
  if (availableFeatures === DashboardFeatures.RESTRICTED) {
    return [Graph.SERVICE_STATS]
  }
  return [...graphSelector[hostSelection][serviceSelection]]
}
