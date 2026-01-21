/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import { DashboardFeatures } from '@/dashboard/types/dashboard'

import type { WidgetItemList } from '../../../components/WidgetSelection/types'
import { ElementSelection } from '../../../types'
import { Graph } from '../types'

const { _t } = usei18n()

const graphSelector = {
  [ElementSelection.SPECIFIC]: [
    Graph.SITE_OVERVIEW,
    Graph.HOST_STATE,
    Graph.HOST_STATE_SUMMARY,
    Graph.HOST_STATS
  ],
  [ElementSelection.MULTIPLE]: [Graph.SITE_OVERVIEW, Graph.HOST_STATE_SUMMARY, Graph.HOST_STATS]
}

type UseAvailableGraphs = Ref<Graph[]>

export const useSelectGraphTypes = (
  hostSelection: Ref<ElementSelection>,
  availableFeatures: DashboardFeatures
): UseAvailableGraphs => {
  const availableGraphs = ref<Graph[]>([])

  watch(
    hostSelection,
    (newHostSelection): void => {
      availableGraphs.value = getAvailableGraphs(newHostSelection, availableFeatures)
    },
    { deep: true, immediate: true }
  )

  return availableGraphs
}

export const getAvailableGraphs = (
  hostSelection: ElementSelection,
  availableFeatures: DashboardFeatures
): Graph[] => {
  if (availableFeatures === DashboardFeatures.RESTRICTED) {
    return [Graph.HOST_STATS]
  }

  return [...graphSelector[hostSelection]]
}

export const allHostSiteWidgets: WidgetItemList = [
  { id: Graph.SITE_OVERVIEW, label: _t('Site overview'), icon: 'site-overview' },
  { id: Graph.HOST_STATS, label: _t('Host statistics'), icon: 'host-statistics' },
  { id: Graph.HOST_STATE, label: _t('Host state'), icon: 'host-state' },
  { id: Graph.HOST_STATE_SUMMARY, label: _t('Host state summary'), icon: 'host-state-summary' }
]
