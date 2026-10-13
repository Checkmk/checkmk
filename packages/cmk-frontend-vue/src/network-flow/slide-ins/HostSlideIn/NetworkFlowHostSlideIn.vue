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
import HostSlideInOverview from './HostSlideInOverview.vue'

const props = defineProps<{
  open: boolean
  /** IP address whose flow profile the panel shows; null while closed. */
  ip: string | null
}>()

const emit = defineEmits<{ close: [] }>()

const header = computed(() => ({
  title: props.ip ?? '',
  closeButton: true
}))

const content = computed<CmkAsyncContentProps | null>(() => {
  const ip = props.ip
  if (ip === null) {
    return null
  }
  return {
    component: markRaw(HostSlideInOverview),
    load: () => networkFlowContextApi.hostContext(ip)
  }
})
</script>

<template>
  <CmkSlideInDialog :open="open" :header="header" @close="emit('close')">
    <CmkAsyncContent v-if="content" v-bind="content" />
  </CmkSlideInDialog>
</template>
