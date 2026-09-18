<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import { type Colors, type Sizes, type Variants } from 'cmk-ui-library/components/CmkTag.vue'

import codeExample from './UclCmkTagCodeExample.vue?raw'

export const panelConfig = {
  content: {
    type: 'string' as const,
    title: 'Content',
    initialState: 'Status Tag'
  },
  size: {
    type: 'list' as const,
    title: 'Size',
    options: listOptions<Sizes>({
      small: 'Small',
      medium: 'Medium',
      large: 'Large'
    }),
    initialState: 'medium' as const
  },
  color: {
    type: 'list' as const,
    title: 'Color',
    options: listOptions<Colors>({
      default: 'Default',
      success: 'Success',
      warning: 'Warning',
      unknown: 'Unknown',
      danger: 'Danger',
      discovered: 'Discovered',
      explicit: 'Explicit',
      ruleset: 'Ruleset',
      label: 'Label'
    }),
    initialState: 'default' as const
  },
  variant: {
    type: 'list' as const,
    title: 'Variant',
    options: listOptions<Variants>({
      outline: 'Outline',
      fill: 'Fill',
      weighted: 'Weighted'
    }),
    initialState: 'outline' as const
  },
  title: {
    type: 'string' as const,
    title: 'Title',
    initialState: '',
    help: 'Native tooltip shown on hover, e.g. the full text when the tag is clipped.'
  }
} satisfies PanelConfigFor<typeof CmkTag>
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
import CmkTag from 'cmk-ui-library/components/CmkTag.vue'

import UclCmkTagDev from './UclCmkTagDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkTag>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkTag</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkTag
        :content="propState.content"
        :size="propState.size"
        :color="propState.color"
        :variant="propState.variant"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkTagDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
