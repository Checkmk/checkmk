<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import { allIconOptions } from '@ucl/_ucl/lib/icon'

import type { CmkIconVariants, IconSizeNames, SimpleIcons } from '@/components/CmkIcon'

import codeExample from './UclCmkIconCodeExample.vue?raw'

export const panelConfig = {
  name: {
    type: 'list' as const,
    title: 'Icon Name',
    initialState: 'main-help',
    options: allIconOptions
  },
  variant: {
    type: 'list' as const,
    title: 'Variant',
    options: [
      { title: 'Plain', name: 'plain' },
      { title: 'Inline (with margin)', name: 'inline' }
    ],
    initialState: 'plain'
  },
  size: {
    type: 'list' as const,
    title: 'Size',
    options: [
      { title: 'XX-Small', name: 'xxsmall' },
      { title: 'X-Small', name: 'xsmall' },
      { title: 'Small', name: 'small' },
      { title: 'Medium', name: 'medium' },
      { title: 'Large', name: 'large' },
      { title: 'X-Large', name: 'xlarge' },
      { title: 'XX-Large', name: 'xxlarge' },
      { title: 'XXX-Large', name: 'xxxlarge' }
    ],
    initialState: 'xxlarge'
  },
  colored: { type: 'boolean' as const, title: 'Colored', initialState: false },
  title: { type: 'string' as const, title: 'Title (Tooltip/Alt)', initialState: 'Help Icon' },
  rotate: { type: 'number' as const, title: 'Rotation (Degrees)', initialState: 0 }
} satisfies PanelConfigFor<typeof CmkIcon>
</script>

<script setup lang="ts">
import {
  PanelStateCreator,
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageDeveloperPlayground,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'

import CmkIcon from '@/components/CmkIcon'

import UclCmkIconDev from './UclCmkIconDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkIcon>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkIcon</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkIcon
        :name="propState.name as SimpleIcons"
        :variant="propState.variant as CmkIconVariants['variant']"
        :size="propState.size as IconSizeNames"
        :colored="propState.colored"
        :title="propState.title"
        :rotate="propState.rotate"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkIconDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
