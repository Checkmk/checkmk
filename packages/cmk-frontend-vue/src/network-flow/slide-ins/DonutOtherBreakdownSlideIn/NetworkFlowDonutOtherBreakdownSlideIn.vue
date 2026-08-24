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

import type { NetworkFlowDonutContent } from '@/dashboard/types/widget'
import { previousWindowLabel } from '@/network-flow/format'

import { networkFlowContextApi } from '../api/context'
import type { DonutOtherBreakdownTarget } from '../injectionKeys'
import DonutOtherBreakdownOverview from './DonutOtherBreakdownOverview.vue'

const { _t } = usei18n()

const props = defineProps<{
  open: boolean
  /** The donut whose remainder the panel breaks down; null while closed. */
  target: DonutOtherBreakdownTarget | null
}>()

const emit = defineEmits<{ close: [] }>()

// The title is the dialog's accessible name, so it names the dimension. Keyed by
// it rather than tested for one, so a third dimension does not read as the first.
const PANEL_TITLE: Record<NetworkFlowDonutContent['dimension'], () => string> = {
  applications: () => _t('Other applications'),
  protocols: () => _t('Other protocols')
}

const header = computed(() => ({
  title: PANEL_TITLE[props.target?.content.dimension ?? 'applications'](),
  closeButton: true
}))

const tabs = computed<SlideInTab[]>(() => {
  const target = props.target
  if (target === null) {
    return []
  }
  return [
    {
      id: 'breakdown',
      title: _t('Breakdown'),
      component: markRaw(DonutOtherBreakdownOverview),
      load: () =>
        networkFlowContextApi.donutOtherBreakdown(target.content, target.context, target.window),
      // The panel's own table heads its comparison the way the legend does.
      props: { previousLabel: previousWindowLabel(target.window) }
    }
  ]
})
</script>

<template>
  <CmkSlideInTabbed :open="open" :tabs="tabs" :header="header" @close="emit('close')" />
</template>
