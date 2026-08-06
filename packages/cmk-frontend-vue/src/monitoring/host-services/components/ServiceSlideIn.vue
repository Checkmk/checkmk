<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSlideInTabbed, { type SlideInTab } from 'cmk-ui-library/components/CmkSlideInTabbed'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, markRaw } from 'vue'

import { HostServicesApi } from '@/monitoring/host-services/api/services'
import type { HostRef, HostServiceEntry } from '@/monitoring/shared/api/types'

import ServiceOverviewSkeleton from './slide-in/ServiceOverviewSkeleton.vue'
import ServiceOverviewTab from './slide-in/ServiceOverviewTab.vue'

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
      load: () => servicesApi.fetchServiceOverview({ host: props.host, description: service.name })
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
  />
</template>
