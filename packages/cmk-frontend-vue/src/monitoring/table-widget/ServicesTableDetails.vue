<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import ServiceSlideIn, {
  SERVICE_GRAPHS_TAB_ID
} from '@/monitoring/host-services/components/ServiceSlideIn.vue'
import type { HostRef } from '@/monitoring/shared/api/types'
import HostSlideIn from '@/monitoring/shared/components/HostSlideIn.vue'
import type { ActionOutcome } from '@/monitoring/shared/components/action/types'
import { hostRefOfService } from '@/monitoring/shared/objectRefs'
import type { DisplayOptions } from '@/monitoring/shared/types'
import { useHostActions } from '@/monitoring/shared/useHostActions'
import { useServiceActions } from '@/monitoring/shared/useServiceActions'

import type { MonitoringTableActionOffer, ServicesTableSubject } from './tableDescriptors'

const props = defineProps<{
  subject: ServicesTableSubject | null
  offer: MonitoringTableActionOffer | undefined
  displayOptions: DisplayOptions
}>()

const emit = defineEmits<{
  close: []
  performed: [outcome: ActionOutcome]
}>()

const NO_HOST: HostRef = { name: '', site_id: '' }

const serviceActions = computed(() => useServiceActions({ actions: props.offer?.actions ?? [] }))

const hostActions = computed(() =>
  useHostActions({ actions: props.offer?.host_actions ?? [], links: props.offer?.host_links ?? [] })
)

const service = computed(() => (props.subject?.kind === 'service' ? props.subject.service : null))

const host = computed(() => (props.subject?.kind === 'host' ? props.subject.host : null))

const serviceHost = computed<HostRef>(() =>
  service.value === null ? NO_HOST : hostRefOfService(service.value)
)

const serviceTabId = ref<string | undefined>(undefined)
const hostTabId = ref<string | undefined>(undefined)

watch(
  () => props.subject,
  (subject) => {
    if (subject?.kind === 'service') {
      serviceTabId.value = subject.graphs ? SERVICE_GRAPHS_TAB_ID : undefined
    } else if (subject?.kind === 'host') {
      hostTabId.value = undefined
    }
  }
)

function loadServiceActionMenu(description: string) {
  return serviceActions.value.loadActionMenu(serviceHost.value, description)
}
</script>

<template>
  <ServiceSlideIn
    v-model:active-tab-id="serviceTabId"
    :service="service"
    :host="serviceHost"
    :display-options="displayOptions"
    :actions="serviceActions.registry"
    :permitted-actions="serviceActions.permittedActions"
    :load-action-menu="loadServiceActionMenu"
    @close="emit('close')"
    @performed="emit('performed', $event)"
  />
  <HostSlideIn
    v-model:active-tab-id="hostTabId"
    :host="host"
    :display-options="displayOptions"
    :actions="hostActions.registry"
    :row-actions="hostActions.rowActions"
    :permitted-actions="hostActions.permittedActions"
    :load-action-menu="hostActions.loadActionMenu"
    @close="emit('close')"
    @performed="emit('performed', $event)"
  />
</template>
