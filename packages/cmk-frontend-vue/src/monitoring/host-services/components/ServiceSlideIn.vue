<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import CmkSlideInTabbed, { type SlideInTab } from 'cmk-ui-library/components/CmkSlideInTabbed'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, markRaw, ref, watch } from 'vue'

import TableSkeleton from '@/loading-transition/TableSkeleton.vue'
import EventHistoryApp from '@/monitoring/events/EventHistoryApp.vue'
import { fetchEvents } from '@/monitoring/events/api'
import { ServiceGraphsApi } from '@/monitoring/host-services/api/graphs'
import { HostServicesApi } from '@/monitoring/host-services/api/services'
import type { HostRef, HostServiceEntry, ServiceOverview } from '@/monitoring/shared/api/types'
import ActionFeedback, {
  type ActionFeedback as ActionFeedbackResult
} from '@/monitoring/shared/components/action/ActionFeedback.vue'
import MonitoringActionPane from '@/monitoring/shared/components/action/MonitoringActionPane.vue'
import type { MonitoringActionRegistry } from '@/monitoring/shared/components/action/registry'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionButtons.vue'
import SlideInActions from '@/monitoring/shared/components/slide-in/SlideInActions.vue'
import { useSlideInActions } from '@/monitoring/shared/services/useSlideInActions'

import ServiceAiExplainButton from './slide-in/ServiceAiExplainButton.vue'
import ServiceGraphsSkeleton from './slide-in/ServiceGraphsSkeleton.vue'
import ServiceGraphsTab, { type ServiceGraphs } from './slide-in/ServiceGraphsTab.vue'
import ServiceOverviewSkeleton from './slide-in/ServiceOverviewSkeleton.vue'
import ServiceOverviewTab from './slide-in/ServiceOverviewTab.vue'
import ServiceSlideInHeader from './slide-in/ServiceSlideInHeader.vue'

const props = withDefaults(
  defineProps<{
    /** The service to detail. `null` keeps the slide-in closed. */
    service: HostServiceEntry | null
    host: HostRef
    /** Offer the cloud edition's "Explain with AI" action. */
    aiExplain?: boolean
    /** The actions this user may run, as reported by the backend; targets are service names. */
    actions?: MonitoringActionRegistry<string>
    permittedActions?: CellAction[]
    /** Lazy loader for the overflow menu entries of a service. */
    loadActionMenu?: ((service: string) => Promise<CellAction[]>) | undefined
    /** The tab on show, as a `v-model:activeTabId`; forwarded to the panel. */
    activeTabId?: string | undefined
  }>(),
  {
    aiExplain: false,
    actions: () => ({}),
    permittedActions: () => [],
    loadActionMenu: undefined,
    activeTabId: undefined
  }
)

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'performed', result: ActionFeedbackResult): void
  (event: 'update:activeTabId', id: string): void
}>()

const { _t } = usei18n()

const servicesApi = new HostServicesApi()
const graphsApi = new ServiceGraphsApi()

const open = computed(() => props.service !== null)

// The header outlives the tab body, so the loaded overview is kept here rather than only being
// handed to the tab component.
const overview = ref<ServiceOverview | null>(null)

// Only the actions the user may run and that this page actually implements reach the buttons.
const slideInActions = computed(() =>
  props.permittedActions.filter((action) => action.id in props.actions)
)

const targets = computed<string[]>(() => (props.service ? [props.service.name] : []))

const {
  activeActionId,
  runningActionId,
  feedback,
  feedbackOpen,
  openAction,
  closeAction,
  applyFeedback
} = useSlideInActions<string>(
  () => props.actions,
  targets,
  () => props.service,
  (result) => emit('performed', result)
)

watch(
  () => props.service,
  () => {
    overview.value = null
  }
)

async function loadOverview(description: string): Promise<ServiceOverview> {
  const loaded = await servicesApi.fetchServiceOverview({ host: props.host, description })
  // A request started for a service the user has since navigated away from must not win the
  // race against the one for the service now on screen.
  if (props.service?.name === description) {
    overview.value = loaded
  }
  return loaded
}

// The link out lives on the overview, which the first tab loads; a reader landing straight on
// the graphs tab from a URL has none yet, so it is loaded here rather than assumed.
async function loadGraphs(description: string): Promise<ServiceGraphs> {
  const [discovered, loaded] = await Promise.all([
    graphsApi.discover(props.host, description),
    overview.value ?? loadOverview(description)
  ])
  return {
    graphs: discovered.graphs,
    noDataMessage: discovered.noDataMessage,
    graphsLink: loaded.legacy_service_graphs_link
  }
}

// Same shape as the host slide-in: link-only actions rendered as icon buttons in the header.
const inlineActions = computed<CellAction[]>(() => {
  const loaded = overview.value
  if (!loaded) {
    return []
  }
  const actions: CellAction[] = [
    {
      id: 'show_service',
      label: _t('Show details of service %{name}', { name: loaded.name }),
      icon: 'services',
      url: loaded.legacy_service_status_link
    }
  ]
  if (loaded.legacy_service_parameters_link !== null) {
    actions.push({
      id: 'show_parameters',
      label: _t('Parameters of this service'),
      icon: 'rulesets',
      url: loaded.legacy_service_parameters_link
    })
  }
  return actions
})

const actionMenuLoader = computed<(() => Promise<CellAction[]>) | undefined>(() => {
  const service = props.service
  const load = props.loadActionMenu
  if (!service || !load) {
    return undefined
  }
  return () => load(service.name)
})

const tabs = computed<SlideInTab[]>(() => {
  const service = props.service
  if (!service) {
    return []
  }
  return [
    {
      id: 'overview',
      title: _t('Overview'),
      component: markRaw(ServiceOverviewTab),
      skeleton: markRaw(ServiceOverviewSkeleton),
      load: () => loadOverview(service.name)
    },
    {
      id: 'history',
      title: _t('History'),
      component: markRaw(EventHistoryApp),
      skeleton: markRaw(TableSkeleton),
      props: { subject: 'service' },
      load: () => fetchEvents(props.host, service.name)
    },
    {
      id: 'service_graphs',
      title: _t('Service graphs'),
      component: markRaw(ServiceGraphsTab),
      skeleton: markRaw(ServiceGraphsSkeleton),
      load: () => loadGraphs(service.name)
    }
  ]
})
</script>

<template>
  <!--
    Keyed on the service so picking another row while the panel is open remounts the tabs.
    CmkSlideInTabbed only drops its cached tab data when `open` flips, which never happens here.
  -->
  <CmkSlideInTabbed
    :key="service?.name ?? ''"
    :open="open"
    :tabs="tabs"
    :override-active="activeActionId !== null"
    :active-tab-id="activeTabId"
    :header="{ title: _t('Service details'), closeButton: true }"
    @close="emit('close')"
    @update:active-tab-id="emit('update:activeTabId', $event)"
  >
    <template #above-tabs>
      <ServiceSlideInHeader
        v-if="service"
        :service="service"
        :modes="overview?.modes ?? []"
        :actions="inlineActions"
        :load-action-menu="actionMenuLoader"
      />
      <ServiceAiExplainButton v-if="aiExplain && overview" :overview="overview" />
    </template>
    <template v-if="slideInActions.length" #actions>
      <SlideInActions
        :actions="slideInActions"
        :running-action-id="runningActionId"
        @select="openAction"
      />
      <ActionFeedback
        v-if="feedback"
        v-model:open="feedbackOpen"
        class="monitoring-service-slide-in__feedback"
        :feedback="feedback"
      />
    </template>
    <template #override>
      <CmkButton variant="optional" class="monitoring-service-slide-in__back" @click="closeAction">
        <CmkIcon name="back" size="small" />
        {{ _t('Back to service detail view') }}
      </CmkButton>
      <MonitoringActionPane
        v-if="activeActionId"
        :action-id="activeActionId"
        :actions="actions"
        :targets="targets"
        indent
        :show-count="false"
        @cancel="closeAction"
        @feedback="applyFeedback"
      />
    </template>
  </CmkSlideInTabbed>
</template>

<style scoped>
.monitoring-service-slide-in__feedback {
  margin-top: var(--spacing);
}

.monitoring-service-slide-in__back {
  gap: var(--dimension-3);
  margin-bottom: var(--spacing);
}
</style>
