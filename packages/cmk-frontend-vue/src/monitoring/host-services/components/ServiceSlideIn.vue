<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSlideInTabbed, { type SlideInTab } from 'cmk-ui-library/components/CmkSlideInTabbed'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, markRaw, ref, watch } from 'vue'

import { HostServicesApi } from '@/monitoring/host-services/api/services'
import type { HostRef, HostServiceEntry, ServiceOverview } from '@/monitoring/shared/api/types'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionButtons.vue'

import ServiceOverviewSkeleton from './slide-in/ServiceOverviewSkeleton.vue'
import ServiceOverviewTab from './slide-in/ServiceOverviewTab.vue'
import ServiceSlideInHeader from './slide-in/ServiceSlideInHeader.vue'

const props = defineProps<{
  /** The service to detail. `null` keeps the slide-in closed. */
  service: HostServiceEntry | null
  host: HostRef
}>()

const emit = defineEmits<{
  (event: 'close'): void
}>()

const { _t } = usei18n()

const servicesApi = new HostServicesApi()

const open = computed(() => props.service !== null)

// The header outlives the tab body, so the loaded overview is kept here rather than only being
// handed to the tab component.
const overview = ref<ServiceOverview | null>(null)

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
    :header="{ title: _t('Service details'), closeButton: true }"
    @close="emit('close')"
  >
    <template #above-tabs>
      <ServiceSlideInHeader
        v-if="service"
        :service="service"
        :modes="overview?.modes ?? []"
        :actions="inlineActions"
      />
    </template>
  </CmkSlideInTabbed>
</template>
