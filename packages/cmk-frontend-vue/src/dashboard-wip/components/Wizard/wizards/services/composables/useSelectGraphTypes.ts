/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import { ElementSelection } from '@/dashboard-wip/components/Wizard/types'
import { DashboardFeatures } from '@/dashboard-wip/types/dashboard'

export enum Graph {
  SERVICE_STATE = 'SERVICE_STATE',
  SERVICE_STATE_SUMMARY = 'SERVICE_STATE_SUMMARY',
  SERVICE_STATISTICS = 'SERVICE_STATISTICS'
}

const graphSelector = {
  //host
  [ElementSelection.SPECIFIC]: {
    //service
    [ElementSelection.SPECIFIC]: [
      Graph.SERVICE_STATE,
      Graph.SERVICE_STATE_SUMMARY,
      Graph.SERVICE_STATISTICS
    ],
    [ElementSelection.MULTIPLE]: [Graph.SERVICE_STATE_SUMMARY, Graph.SERVICE_STATISTICS]
  },

  //host
  [ElementSelection.MULTIPLE]: {
    //service
    [ElementSelection.SPECIFIC]: [Graph.SERVICE_STATE_SUMMARY, Graph.SERVICE_STATISTICS],
    [ElementSelection.MULTIPLE]: [Graph.SERVICE_STATE_SUMMARY, Graph.SERVICE_STATISTICS]
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
    return [Graph.SERVICE_STATISTICS]
  }
  return [...graphSelector[hostSelection][serviceSelection]]
}
