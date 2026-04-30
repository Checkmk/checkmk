<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkPopupCodeExample.vue?raw'

export const panelConfig = {
  open: {
    type: 'boolean',
    title: 'Open',
    initialState: false
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

import CmkButton from '@/components/CmkButton.vue'
import CmkPopup from '@/components/CmkPopup.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkPopup</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkButton @click="propState.open = true">Open Popup</CmkButton>
      <CmkPopup :open="propState.open" @close="propState.open = false">
        <p>Popup content goes here.</p>
      </CmkPopup>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[{ keys: ['Escape'], description: 'Closes the popup.' }]" />
  </UclDetailPageLayout>
</template>
