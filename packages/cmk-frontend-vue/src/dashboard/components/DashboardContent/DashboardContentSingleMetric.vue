<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import useTimer from 'cmk-ui-library/lib/useTimer'
import { computed, onBeforeMount, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import CmkKpiStatCard, {
  type KpiState,
  type TimestampedSample
} from '@/dashboard/components/CmkKpiStatCard'
import { useInjectCmkToken } from '@/dashboard/composables/useCmkToken'
import { useInjectIsPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'
import type { ComputedSingleMetric, SingleMetricContent } from '@/dashboard/types/widget.ts'
import { dashboardAPI } from '@/dashboard/utils.ts'

import DashboardContentContainer from './DashboardContentContainer.vue'
import type { ContentProps } from './types.ts'

const { _t } = usei18n()
const props = defineProps<ContentProps<SingleMetricContent>>()
const cmkToken = useInjectCmkToken()
const isPublicDashboard = useInjectIsPublicDashboard()

const data = ref<ComputedSingleMetric | undefined>(undefined)
const fetchingErrorMessage = ref<string | null>(null)

const fetchData = async () => {
  try {
    // A shared dashboard has no session to authenticate with, so it names the widget and
    // lets the endpoint read the configuration off the dashboard its token belongs to.
    const response =
      cmkToken === undefined
        ? await dashboardAPI.computeSingleMetricData(
            props.content,
            props.effective_filter_context.filters
          )
        : await dashboardAPI.computeSharedSingleMetricData(props.widget_id, cmkToken)
    data.value = response.value
    fetchingErrorMessage.value = null
  } catch (error) {
    console.error('Error fetching single metric content:', error)
    fetchingErrorMessage.value = `${_t('Failed to fetch single metric data:')} ${(error as Error).message}`
  }
}

// The widget reloads on its own, as the figure it replaces did. The dashboard
// has no configurable refresh interval, so this matches what the graph and
// figure widgets use.
const REFRESH_INTERVAL_MS = 60_000

// A hidden tab does not need current data; coming back into view fetches once
// so the widget is up to date right away rather than after the rest of the
// interval.
const reload = (): void => {
  if (document.hidden) {
    return
  }
  void fetchData()
}

const timer = useTimer(reload, REFRESH_INTERVAL_MS)

onBeforeMount(() => {
  void fetchData()
})

onMounted(() => {
  timer.start()
  document.addEventListener('visibilitychange', reload)
})

onBeforeUnmount(() => {
  timer.stop()
  document.removeEventListener('visibilitychange', reload)
})

const dataParameters = computed(() =>
  JSON.stringify({ filters: props.effective_filter_context.filters, content: props.content })
)

watch(dataParameters, () => {
  void fetchData()
})

// The card renders the value as a link into the service view it was read from,
// which a public dashboard must not offer.
const href = computed(() => (isPublicDashboard ? undefined : (data.value?.url ?? undefined)))

const state = computed<KpiState | undefined>(() => {
  const reported = data.value?.state
  return reported
    ? { severity: reported.severity, tintBackground: reported.tint_background }
    : undefined
})

// The single metric endpoint (cmk/gui/nonfree/pro/dashboard/_single_metric_data.py)
// drops timestamps and filters out None values before they reach here, so it
// cannot express gaps or staleness. The index is used as a stand-in timestamp
// purely to satisfy CmkKpiStatCard's contract - it does not represent real time,
// and this card never shows a real gap until that endpoint is migrated.
const series = computed<TimestampedSample[]>(
  () => data.value?.series.map((value, index) => ({ timestamp: index, value })) ?? []
)
</script>

<template>
  <DashboardContentContainer
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    content-overflow="hidden"
  >
    <div class="db-content-single-metric__wrapper">
      <div v-if="fetchingErrorMessage" class="db-content-single-metric__error">
        <CmkAlertBox variant="error">{{ fetchingErrorMessage }}</CmkAlertBox>
      </div>
      <CmkLoading v-else-if="data === undefined" />
      <CmkKpiStatCard
        v-else
        :title="effectiveTitle"
        :value="data.value"
        :unit="data.unit"
        :series="series"
        :color="data.color"
        :state="state"
        :range-limits="data.range_limits"
        :href="href"
      />
    </div>
  </DashboardContentContainer>
</template>

<style scoped>
/* No padding: the card fills the widget, so that the state tint and the spark
   line reach the widget's own edges. The card insets its own content. */
.db-content-single-metric__wrapper {
  display: flex;
  flex: 1;
  min-height: 0;
}

.db-content-single-metric__error {
  margin: auto;
  max-width: 90%;
}
</style>
