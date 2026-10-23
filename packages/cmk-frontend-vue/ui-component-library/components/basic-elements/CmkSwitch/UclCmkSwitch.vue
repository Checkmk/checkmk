<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkSwitchCodeExample.vue?raw'

export const panelConfig = {
  modelValue: {
    type: 'boolean' as const,
    title: 'Checked State',
    initialState: false
  },
  ariaLabel: {
    type: 'string' as const,
    title: 'Accessible name',
    initialState: 'Use color'
  },
  ariaLabelledby: {
    type: 'string' as const,
    title: 'Labelled by (element id)',
    initialState: ''
  }
} satisfies PanelConfigFor<typeof CmkSwitch>
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
import CmkSwitch from 'cmk-ui-library/components/CmkSwitch.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkSwitch>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkSwitch</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkSwitch
        v-model="propState.modelValue"
        :aria-label="propState.ariaLabel || undefined"
        :aria-labelledby="propState.ariaLabelledby || undefined"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
