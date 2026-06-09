<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkSearchInputCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to the search field.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the search field from the next focusable element in reverse order.'
  },
  {
    keys: ['Enter'],
    description: 'Submits the current query, emitting the search event.'
  }
]

export const panelConfig = {
  modelValue: {
    type: 'string' as const,
    title: 'Query',
    initialState: ''
  },
  placeholder: {
    type: 'string' as const,
    title: 'Placeholder',
    initialState: 'Search hosts…'
  }
} satisfies PanelConfigFor<typeof CmkSearchInput>
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
import { ref } from 'vue'

import CmkSearchInput from '@/components/CmkSearchInput.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkSearchInput>().createRef(panelConfig)

const lastSearch = ref('')
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkSearchInput</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div>
        <CmkSearchInput
          v-model="propState.modelValue"
          :placeholder="propState.placeholder"
          @search="lastSearch = $event"
        />
        <CmkParagraph>Last submitted query: {{ lastSearch || '—' }}</CmkParagraph>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
