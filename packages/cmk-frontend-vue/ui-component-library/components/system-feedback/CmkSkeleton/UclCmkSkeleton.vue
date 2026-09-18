<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import { type SkeletonType } from 'cmk-ui-library/components/CmkSkeleton.vue'

import codeExample from './UclCmkSkeletonCodeExample.vue?raw'

export const panelConfig = {
  type: {
    type: 'list' as const,
    title: 'Skeleton Type',
    options: listOptions<NonNullable<SkeletonType>>({
      box: 'Box',
      h1: 'H1',
      h2: 'H2',
      h3: 'H3',
      text: 'Text',
      'info-text': 'Info Text',
      'icon-xsmall': 'Icon: X-Small',
      'icon-small': 'Icon: Small',
      'icon-medium': 'Icon: Medium',
      'icon-large': 'Icon: Large',
      'icon-xlarge': 'Icon: X-Large',
      'icon-xxlarge': 'Icon: XX-Large',
      'icon-xxxlarge': 'Icon: XXX-Large'
    }),
    initialState: 'text' as const
  },
  width: {
    type: 'string' as const,
    title: 'Custom Width',
    help: 'Optionally set a custom width for the skeleton using any valid CSS unit(% or px).',
    initialState: '100%'
  }
} satisfies PanelConfigFor<typeof CmkSkeleton>
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
import CmkSkeleton from 'cmk-ui-library/components/CmkSkeleton.vue'

import UclCmkSkeletonDev from './UclCmkSkeletonDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkSkeleton>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkSkeleton</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkSkeleton :type="propState.type" :width="propState.width" />
      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkSkeletonDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
