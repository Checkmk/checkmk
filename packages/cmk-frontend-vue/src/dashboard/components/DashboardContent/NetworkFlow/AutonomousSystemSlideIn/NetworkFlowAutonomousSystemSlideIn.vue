<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSlideInTabbed from 'cmk-ui-library/components/CmkSlideInTabbed'
import type { SlideInTab } from 'cmk-ui-library/components/CmkSlideInTabbed'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, markRaw } from 'vue'

import { dashboardAPI } from '@/dashboard/utils.ts'

import AutonomousSystemSlideInOverview from './AutonomousSystemSlideInOverview.vue'

const { _t } = usei18n()

const props = defineProps<{
  open: boolean
  /** Autonomous system number whose flow profile the panel shows; null while closed. */
  asn: number | null
}>()

const emit = defineEmits<{ close: [] }>()

const header = computed(() => ({
  title: props.asn === null ? '' : `AS${props.asn}`,
  closeButton: true
}))

const tabs = computed<SlideInTab[]>(() => {
  const asn = props.asn
  if (asn === null) {
    return []
  }
  return [
    {
      id: 'overview',
      title: _t('Overview'),
      component: markRaw(AutonomousSystemSlideInOverview),
      load: async () => (await dashboardAPI.computeNetworkFlowAutonomousSystemContext(asn)).value
    }
  ]
})
</script>

<template>
  <CmkSlideInTabbed :open="open" :tabs="tabs" :header="header" @close="emit('close')" />
</template>
