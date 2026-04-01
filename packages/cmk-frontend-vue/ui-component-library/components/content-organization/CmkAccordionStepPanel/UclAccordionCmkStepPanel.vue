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
export const codeExample = `<script setup lang="ts">
import { ref } from 'vue'
${'import'} CmkAccordionStepPanel from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanel.vue'
${'import'} CmkAccordionStepPanelItem from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'

const openSteps = ref(['step-2'])
<${'/'}script>

<template>
  <CmkAccordionStepPanel v-model="openSteps">

    <CmkAccordionStepPanelItem
      :step="1"
      title="Download Agent"
      info="2-3 min"
      :accomplished="true"
    >
      <p>Select your operating system and download the appropriate agent package.</p>
    </CmkAccordionStepPanelItem>

    <CmkAccordionStepPanelItem
      :step="2"
      title="Install Package"
      info="5 min"
      :accomplished="false"
    >
      <p>Run the installer on your target machine. Ensure you have root/admin privileges.</p>
    </CmkAccordionStepPanelItem>
  </CmkAccordionStepPanel>
</template>`
export const panelConfig = {
  openSteps: {
    type: 'string-array',
    title: 'openSteps',
    initialState: ['step-2'],
    help: "Type: string[]. IDs are auto-generated as step-{n} from each item's step prop. In the UCL app, enter one ID per line in the textarea, e.g.:step-1 step-2 step-3"
  }
} satisfies PanelConfig
export const itemPanelConfig = {
  accomplished: {
    type: 'boolean',
    title: 'accomplished',
    initialState: false,
    help: 'Marks items as completed, showing a checkmark badge.'
  },
  disabled: {
    type: 'boolean',
    title: 'disabled',
    initialState: false,
    help: 'Disables all items, preventing them from being expanded.'
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

import CmkAccordionStepPanel from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanel.vue'
import CmkAccordionStepPanelItem from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'
import CmkIndent from '@/components/CmkIndent.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))

const itemPropState = ref(createPanelState(itemPanelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkAccordionStepPanel</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkAccordionStepPanel v-model="propState.openSteps">
        <CmkAccordionStepPanelItem
          :step="1"
          title="Download Agent"
          info="2-3 min"
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
