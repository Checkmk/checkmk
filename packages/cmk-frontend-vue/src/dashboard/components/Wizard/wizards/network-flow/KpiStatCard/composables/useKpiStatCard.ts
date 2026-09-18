/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { type Ref, computed, ref, watch } from 'vue'

import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type { UseWidgetHandler, WidgetProps } from '@/dashboard/components/Wizard/types'
import { useInjectDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import { usePreviewWidgetTitle } from '@/dashboard/composables/useWidgetTitles'
import type { NetworkFlowKpiStatCardContent, WidgetSpec } from '@/dashboard/types/widget'
import { buildWidgetEffectiveFilterContext } from '@/dashboard/utils'

const CONTENT_TYPE = 'network_flow_kpi_stat_card'

type Metric = NetworkFlowKpiStatCardContent['metric']
type Accent = NetworkFlowKpiStatCardContent['accent']
type SparkHeightMode = NetworkFlowKpiStatCardContent['spark_height_mode']

// Mockup defaults: the byte volumes use the traffic report's card colors,
// the activity counts the overview's.
const suggestedAccent: Record<Metric, Accent> = {
  total_bytes: 'green',
  ingress_bytes: 'blue',
  egress_bytes: 'magenta',
  active_hosts: 'green',
  total_flows: 'blue',
  active_asn: 'green',
  peak_throughput: 'yellow',
  avg_throughput: 'magenta',
  tracked_hosts: 'green'
}

export interface UseKpiStatCard extends UseWidgetHandler, UseWidgetVisualizationOptions {
  metric: Ref<Metric>
  accent: Ref<Accent>
  showDelta: Ref<boolean>
  sparkHeightMode: Ref<SparkHeightMode>
}

export function useKpiStatCard(currentSpec: WidgetSpec | null): UseKpiStatCard {
  const { _t } = usei18n()
  const constants = useInjectDashboardConstants()

  // Default widget title per metric; mirrors the metric dropdown labels.
  const metricTitles: Record<Metric, string> = {
    total_bytes: _t('Total bytes'),
    ingress_bytes: _t('Ingress bytes'),
    egress_bytes: _t('Egress bytes'),
    active_hosts: _t('Active hosts'),
    total_flows: _t('Total flows'),
    active_asn: _t('Active ASN'),
    peak_throughput: _t('Peak throughput'),
    avg_throughput: _t('Avg throughput'),
    tracked_hosts: _t('Tracked hosts')
  }

  const currentContent =
    currentSpec?.content?.type === CONTENT_TYPE
      ? (currentSpec?.content as NetworkFlowKpiStatCardContent)
      : undefined
  const initialMetric: Metric = currentContent?.metric ?? 'total_bytes'

  const {
    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,
    titleUrlValidationErrors,
    validate: validateVisualization,
    widgetGeneralSettings,
    titleMacros
  } = useWidgetVisualizationProps(
    metricTitles[initialMetric],
    currentSpec?.general_settings,
    CONTENT_TYPE
  )

  const metric = ref<Metric>(initialMetric)
  const accent = ref<Accent>(currentContent?.accent ?? suggestedAccent[metric.value])
  const showDelta = ref<boolean>(currentContent?.show_delta ?? true)
  const sparkHeightMode = ref<SparkHeightMode>(currentContent?.spark_height_mode ?? 'band')

  // Changing the metric resets the accent to the suggested one and, unless
  // the user has customized the title, updates it to the new metric's
  // default. The user can still override both afterwards.
  watch(metric, (newMetric, oldMetric) => {
    accent.value = suggestedAccent[newMetric]
    if (title.value === metricTitles[oldMetric]) {
      title.value = metricTitles[newMetric]
    }
  })

  function validate(): boolean {
    return validateVisualization()
  }

  const content = computed<NetworkFlowKpiStatCardContent>(() => {
    return {
      type: CONTENT_TYPE,
      metric: metric.value,
      accent: accent.value,
      show_delta: showDelta.value,
      spark_height_mode: sparkHeightMode.value
    }
  })

  const effectiveTitle = usePreviewWidgetTitle(
    computed(() => {
      return {
        generalSettings: widgetGeneralSettings.value,
        content: content.value,
        effectiveFilters: {}
      }
    })
  )

  const widgetProps = computed<WidgetProps>(() => {
    return {
      general_settings: widgetGeneralSettings.value,
      content: content.value,
      effectiveTitle: effectiveTitle.value,
      effective_filter_context: buildWidgetEffectiveFilterContext(
        content.value,
        {},
        [], // filters are not wired into the flow queries yet
        constants
      )
    }
  })

  return {
    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,
    titleUrlValidationErrors,
    titleMacros,
    validate,

    metric,
    accent,
    showDelta,
    sparkHeightMode,

    widgetProps,
    getSubmitProps: async () => widgetProps.value
  }
}
