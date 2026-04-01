<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Moves keyboard focus to title. While the focus outline is hidden from view, its underlying functionality remains intact.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the title from the next focusable element in reverse order.'
  },
  {
    keys: ['Enter', 'Space'],
    description:
      'When the title button is focused, pressing Enter or Space opens the collapsible content.'
  }
]
export const codeExample = `<script setup lang="ts">
import { ref } from 'vue'
${'import'} CmkCollapsible, { CmkCollapsibleTitle } from '@/components/CmkCollapsible'
${'import'} CmkIndent from '@/components/CmkIndent.vue'

const isOpen = ref(false)
<${'/'}script>

<template>
  <CmkCollapsibleTitle
    title="Collapsible Section"
    side-title="Details"
    help_text="Click to expand"
    :open="isOpen"
    @toggle-open="isOpen = !isOpen"
  />

  <CmkCollapsible :open="isOpen">
    <CmkIndent>
      This content is hidden inside the collapsible wrapper. It animates height smoothly when toggled.
    </CmkIndent>
  </CmkCollapsible>
</template>`
export const panelConfig = {
  open: { type: 'boolean', title: 'Open', initialState: false },
  title: { type: 'string', title: 'Title Text', initialState: 'Collapsible Section' },
  sideTitle: { type: 'string', title: 'Side Title', initialState: 'Details' },
  helpText: { type: 'string', title: 'Help Text', initialState: 'Click to expand' }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageDeveloperPlayground,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel,
  createPanelState
} from '@ucl/_ucl/components/detail-page'
import { ref } from 'vue'

import CmkCollapsible, { CmkCollapsibleTitle } from '@/components/CmkCollapsible'
import CmkIndent from '@/components/CmkIndent.vue'

import UclCmkCollapsibleDev from './UclCmkCollapsibleDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkCollapsible</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkCollapsibleTitle
        :title="propState.title"
        :side-title="propState.sideTitle"
        :help_text="propState.helpText"
        :open="propState.open"
        @toggle-open="propState.open = !propState.open"
      />

      <CmkCollapsible :open="propState.open">
        <CmkIndent>
          This content is hidden inside the collapsible wrapper. It animates height smoothly when
          toggled.
        </CmkIndent>
      </CmkCollapsible>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkCollapsibleDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
