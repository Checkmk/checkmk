<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import type { Colors, FontColors, Sizes } from '@/components/progress/CmkProgressCircle.vue'

import codeExample from './UclCmkProgressCircleCodeExample.vue?raw'

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
  color: {
    type: 'list' as const,
    title: 'Color',
    options: [
      { title: 'Success', name: 'success' },
      { title: 'Warning', name: 'warning' },
      { title: 'Danger', name: 'danger' }
    ] satisfies Options<NonNullable<Colors>>[],
    initialState: 'success' as const
  },
  fontColor: {
    type: 'list' as const,
    title: 'Font Color',
    options: [
      { title: 'Success', name: 'success' },
      { title: 'Warning', name: 'warning' },
      { title: 'Danger', name: 'danger' }
    ] satisfies Options<NonNullable<FontColors>>[],
    initialState: 'success' as const
  },
  label: { type: 'boolean' as const, title: 'label', initialState: true },
  reverse: { type: 'boolean' as const, title: 'reverse (countdown)', initialState: false }
} satisfies PanelConfigFor<typeof CmkProgressCircle>
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

import CmkProgressCircle from '@/components/progress/CmkProgressCircle.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkProgressCircle>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkProgressCircle</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkProgressCircle
        :value="propState.value"
        :max="propState.max ? Number(propState.max) : 'unknown'"
        :size="propState.size"
        :color="propState.color"
        :font-color="propState.fontColor"
        :label="propState.label ? { showTotal: true, unit: '%' } : undefined"
        :reverse="propState.reverse"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
