<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import type { Sizes } from '@/components/progress/CmkProgressbar.vue'

import codeExample from './UclCmkProgressbarCodeExample.vue?raw'

export const panelConfig = {
  value: { type: 'number' as const, title: 'Current Value', initialState: 30 },
  max: {
    type: 'string' as const,
    title: 'Max Value',
    initialState: '100',
    help: 'Leave empty for infinite mode'
  },
  size: {
    type: 'list' as const,
    title: 'Size',
    options: [
      { title: 'Small', name: 'small' },
      { title: 'Medium', name: 'medium' },
      { title: 'Large', name: 'large' }
    ] satisfies Options<NonNullable<Sizes>>[],
    initialState: 'medium' as const
  },
  label: { type: 'boolean' as const, title: 'label', initialState: true }
} satisfies PanelConfigFor<typeof CmkProgressbar>
</script>

<script setup lang="ts">
import {
  PanelStateCreator,
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'

import CmkProgressbar from '@/components/progress/CmkProgressbar.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkProgressbar>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkProgressbar</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkProgressbar
        :value="propState.value"
        :max="propState.max ? Number(propState.max) : 'unknown'"
        :size="propState.size"
        :label="propState.label ? { showTotal: true, unit: '%' } : undefined"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
