<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { StringPropDef } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkLabeledSwitchCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to the switch.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the switch from the next focusable element in reverse order.'
  },
  {
    keys: ['Space'],
    description: 'Toggles the switch between its two states.'
  },
  {
    keys: ['Enter'],
    description: 'Toggles the switch between its two states.'
  }
]

export const panelConfig = {
  modelValue: {
    type: 'boolean' as const,
    title: 'On State',
    initialState: false
  },
  offLabel: {
    type: 'string' as const,
    title: 'Off Label',
    initialState: 'Time zoom'
  },
  onLabel: {
    type: 'string' as const,
    title: 'On Label',
    initialState: 'Peak zoom'
  },
  offHelp: {
    type: 'string' as const,
    title: 'Off Help',
    initialState: 'Drag to zoom into a time range.'
  },
  onHelp: {
    type: 'string' as const,
    title: 'On Help',
    initialState: 'Drag to zoom into a value range.'
  }
  // `onLabel` and `onHelp` are real props, but Vue's typing treats an `on`-prefixed name as
  // an event handler, so PanelConfigFor can't see them — declare their knob types explicitly.
} satisfies PanelConfigFor<typeof CmkLabeledSwitch> & {
  onLabel: StringPropDef
  onHelp: StringPropDef
}
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
import CmkLabeledSwitch from 'cmk-ui-library/components/CmkLabeledSwitch.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkLabeledSwitch>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkLabeledSwitch</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkLabeledSwitch
        v-model="propState.modelValue"
        :off-label="propState.offLabel"
        :on-label="propState.onLabel"
        :off-help="propState.offHelp"
        :on-help="propState.onHelp"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
