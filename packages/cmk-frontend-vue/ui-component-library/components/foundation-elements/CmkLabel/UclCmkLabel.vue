<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type LabelProps } from '@/components/CmkLabel.vue'

import codeExample from './UclCmkLabelCodeExample.vue?raw'

export const panelConfig = {
  variant: {
    type: 'list' as const,
    title: 'Variant',
    options: [
      { title: 'Default', name: 'default' },
      { title: 'Title', name: 'title' },
      { title: 'Subtitle', name: 'subtitle' }
    ] satisfies Options<LabelProps['variant']>[],
    initialState: 'default' as const
  },
  dots: {
    type: 'boolean' as const,
    title: 'Dots',
    initialState: false
  },
  cursor: {
    type: 'list' as const,
    title: 'Cursor',
    options: [
      { title: 'Default', name: 'default' },
      { title: 'Pointer', name: 'pointer' }
    ] satisfies Options<LabelProps['cursor']>[],
    initialState: 'default' as const
  },
  help: {
    type: 'string' as const,
    title: 'Help Text',
    initialState: ''
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel,
  createPanelState
} from '@ucl/_ucl/components/detail-page'
import { ref } from 'vue'

import CmkLabel from '@/components/CmkLabel.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkLabel</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkLabel :variant="propState.variant" :dots="propState.dots" :cursor="propState.cursor">
        Form Field
      </CmkLabel>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
