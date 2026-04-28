<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, type StringPropDef } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkButtonSubmitCodeExample.vue?raw'

export const panelConfig = {
  label: {
    type: 'string' as const,
    title: 'Label',
    initialState: 'Save'
  },
  disabled: {
    type: 'boolean' as const,
    title: 'Disabled',
    initialState: false
  },
  title: {
    type: 'string' as const,
    title: 'Title',
    initialState: ''
  }
} satisfies PanelConfigFor<typeof CmkButtonSubmit> & { label: StringPropDef }
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

import CmkButtonSubmit from '@/components/CmkButtonSubmit.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkButtonSubmit</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkButtonSubmit :disabled="propState.disabled" :title="propState.title">
        {{ propState.label }}
      </CmkButtonSubmit>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
