<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { StringArrayPropDef } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkAccordionStepPanelCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to the step panel.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the step panel from the next focusable element in reverse order.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'Toggles the expansion state of the focused accordion item.'
  }
]

export const panelConfig = {
  openSteps: {
    type: 'string-array' as const,
    title: 'openSteps',
    initialState: ['step-2'],
    help: "Type: string[]. IDs are auto-generated as step-{n} from each item's step prop. In the UCL app, enter one ID per line in the textarea, e.g.:step-1 step-2 step-3"
  }
} satisfies PanelConfigFor<typeof CmkAccordionStepPanel, 'modelValue'> & {
  openSteps: StringArrayPropDef
}
export const itemPanelConfig = {
  step: {
    type: 'number' as const,
    title: 'step',
    initialState: 1
  },
  title: {
    type: 'string' as const,
    title: 'title',
    initialState: 'Step Title'
  },
  accomplished: {
    type: 'boolean' as const,
    title: 'accomplished',
    initialState: false,
    help: 'Marks items as completed, showing a checkmark badge.'
  },
  disabled: {
    type: 'boolean' as const,
    title: 'disabled',
    initialState: false,
    help: 'Disables all items, preventing them from being expanded.'
  },
  info: {
    type: 'string' as const,
    title: 'info',
    initialState: '2-3 min',
    help: 'Short hint displayed next to the step title (e.g. estimated duration).'
  }
} satisfies PanelConfigFor<typeof CmkAccordionStepPanelItem>
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

import CmkAccordionStepPanel from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanel.vue'
import CmkAccordionStepPanelItem from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'
import CmkIndent from '@/components/CmkIndent.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkAccordionStepPanel, 'modelValue'>().createRef(
  panelConfig
)

const itemPropState = new PanelStateCreator<typeof CmkAccordionStepPanelItem>().createRef(
  itemPanelConfig
)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkAccordionStepPanel</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkAccordionStepPanel v-model="propState.openSteps">
        <CmkAccordionStepPanelItem
          :step="1"
          title="Download Agent"
          :info="itemPropState.info"
          :accomplished="itemPropState.accomplished"
          :disabled="itemPropState.disabled"
        >
          <CmkIndent>
            Select your operating system and download the appropriate agent package.
          </CmkIndent>
        </CmkAccordionStepPanelItem>

        <CmkAccordionStepPanelItem
          :step="2"
          title="Install Package"
          info="5 min"
          :accomplished="itemPropState.accomplished"
          :disabled="itemPropState.disabled"
        >
          <CmkIndent>
            Run the installer on your target machine. Ensure you have root/admin privileges.
          </CmkIndent>
        </CmkAccordionStepPanelItem>

        <CmkAccordionStepPanelItem
          :step="3"
          title="Verify Connection"
          info="&infin;"
          :accomplished="itemPropState.accomplished"
          :disabled="itemPropState.disabled"
        >
          <CmkIndent> Check the connection status in the monitoring dashboard. </CmkIndent>
        </CmkAccordionStepPanelItem>
      </CmkAccordionStepPanel>

      <template #properties>
        <UclPropertiesPanel
          v-model="propState"
          title="CmkAccordionStepPanel"
          :config="panelConfig"
        />
        <UclPropertiesPanel
          v-model="itemPropState"
          title="CmkAccordionStepPanelItem"
          :config="itemPanelConfig"
        />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
