<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAsyncContent from 'cmk-ui-library/components/CmkAsyncContent'
import type { CmkAsyncContentProps } from 'cmk-ui-library/components/CmkAsyncContent'
import CmkSlideInDialog from 'cmk-ui-library/components/CmkSlideInDialog.vue'
import { computed, markRaw } from 'vue'

import { networkFlowContextApi } from '../api/context'
import AutonomousSystemSlideInOverview from './AutonomousSystemSlideInOverview.vue'

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

const content = computed<CmkAsyncContentProps | null>(() => {
  const asn = props.asn
  if (asn === null) {
    return null
  }
  return {
    component: markRaw(AutonomousSystemSlideInOverview),
    load: () => networkFlowContextApi.autonomousSystemContext(asn)
  }
})
</script>

<template>
  <CmkSlideInDialog :open="open" :header="header" @close="emit('close')">
    <CmkAsyncContent v-if="content" v-bind="content" />
  </CmkSlideInDialog>
</template>
