/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import { ElementSelection } from '../../../types'
import { Graph } from '../types'

const graphSelector = {
  [ElementSelection.SPECIFIC]: [
    Graph.SITE_OVERVIEW,
    Graph.HOST_STATE,
    Graph.HOST_STATE_SUMMARY,
    Graph.HOST_STATISTICS
  ],
  [ElementSelection.MULTIPLE]: [
    Graph.SITE_OVERVIEW,
    Graph.HOST_STATE_SUMMARY,
    Graph.HOST_STATISTICS
  ]
}

type UseAvailableGraphs = Ref<Graph[]>

export const useSelectGraphTypes = (hostSelection: Ref<ElementSelection>): UseAvailableGraphs => {
  const availableGraphs = ref<Graph[]>([])

  watch(
    hostSelection,
    (newHostSelection) => {
      availableGraphs.value = [...graphSelector[newHostSelection]]
    },
    { deep: true, immediate: true }
  )

  return availableGraphs
}

export const getAvailableGraphs = (hostSelection: ElementSelection): Graph[] => {
  return [...graphSelector[hostSelection]]
}
