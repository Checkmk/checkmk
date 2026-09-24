<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout
} from '@ucl/_ucl/components/detail-page'
import CmkPointerTooltip, {
  type CmkPointerTooltipPointer
} from 'cmk-ui-library/components/CmkPointerTooltip.vue'
import { ref } from 'vue'

import codeExample from './UclCmkPointerTooltipCodeExample.vue?raw'

defineProps<{ screenshotMode: boolean }>()

const pointer = ref<CmkPointerTooltipPointer | null>(null)

function follow(event: PointerEvent) {
  pointer.value = { clientX: event.clientX, clientY: event.clientY }
}
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkPointerTooltip</UclDetailPageHeader>

    <UclDetailPageComponent>
      <svg width="320" height="160" @pointermove="follow" @pointerleave="pointer = null">
        <rect width="320" height="160" fill="var(--ux-theme-4)" />
      </svg>
      <CmkPointerTooltip :pointer="pointer" @dismiss="pointer = null">
        12 hosts are up
      </CmkPointerTooltip>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
