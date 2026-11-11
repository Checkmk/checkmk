<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkMenu from 'cmk-ui-library/components/CmkMenu'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { useInjectDashboardEditing } from '@/dashboard/composables/useDashboardEditing'
import { useInjectDrillDownSource } from '@/dashboard/composables/useDrillDownSource'
import { drawnServices, graphLinkOffer } from '@/dashboard/lib/graphContextualLinks'
import type {
  GraphLinkContent,
  GraphLinks,
  GraphService,
  VisualContext
} from '@/dashboard/types/widget'
import { dashboardAPI } from '@/dashboard/utils'
import type { Metric, RequestedTimeRange } from '@/graphing'

const { _t } = usei18n()

const props = defineProps<{
  content: GraphLinkContent
  context: VisualContext
  /** The one service a graph is drawn for; null for a graph naming the service of each line. */
  singleService: GraphService | null
  metrics: Metric[]
  timeRange: RequestedTimeRange
  setShown: (shown: boolean) => void
}>()

const editing = useInjectDashboardEditing()
const drillDownSource = useInjectDrillDownSource()

const services = computed(() =>
  props.singleService === null ? drawnServices(props.metrics) : [props.singleService]
)

const resolved = ref<GraphLinks | null>(null)

async function fetchLinks(): Promise<GraphLinks | null> {
  if (services.value.length === 0) {
    return null
  }
  try {
    const response = await dashboardAPI.computeGraphLinks({
      source: { type: 'explicit', content: props.content, context: props.context },
      services: services.value
    })
    return response.value
  } catch {
    // The graph shows without its links; it only offers no way on.
    return null
  }
}

// A refresh draws the same services again, so only a change asks anew.
const requestKey = computed(() =>
  JSON.stringify({ content: props.content, context: props.context, services: services.value })
)
// Latest-wins: discard the answers of superseded requests.
let requestCounter = 0
watch(
  requestKey,
  async () => {
    const counter = ++requestCounter
    const links = await fetchLinks()
    if (counter === requestCounter) {
      resolved.value = links
    }
  },
  { immediate: true }
)

const offer = computed(() =>
  resolved.value === null
    ? { type: 'none' as const }
    : graphLinkOffer(resolved.value, props.metrics, {
        context: props.context,
        drilledFrom: drillDownSource.value,
        timeRange: props.timeRange
      })
)

watch(
  () => offer.value.type !== 'none',
  (shown) => props.setShown(shown),
  { immediate: true }
)
onBeforeUnmount(() => props.setShown(false))

const menuLabel = _t('Contextual links')
const buttonTitle = computed(() =>
  offer.value.type === 'link' ? offer.value.link.title : menuLabel
)
</script>

<template>
  <CmkMenu v-if="offer.type === 'menu' && !editing" :items="offer.items" :label="menuLabel" />
  <!-- While the dashboard is edited, following a link would leave its changes. -->
  <CmkButton
    v-else-if="offer.type !== 'none'"
    size="small"
    :href="offer.type === 'link' && !editing ? offer.link.url : undefined"
    :disabled="editing"
    :title="buttonTitle"
    :aria-label="buttonTitle"
  >
    <CmkMultitoneIcon name="chain" primary-color="font" size="small" aria-hidden="true" />
  </CmkButton>
</template>
