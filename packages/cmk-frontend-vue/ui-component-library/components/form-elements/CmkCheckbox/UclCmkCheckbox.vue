<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import type { ListPropDef } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkCheckboxCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Moves keyboard focus to the checkbox. While the focus outline is hidden from view, its underlying functionality remains intact.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the checkbox from the next focusable element in reverse order.'
  },
  {
    keys: ['Space'],
    description: 'Toggles the checkbox state between checked and unchecked.'
  }
]

type CheckboxPadding = 'both' | 'top' | 'bottom'
type CheckboxLabelPosition = 'left' | 'right'

export const panelConfig = {
  value: {
    type: 'list' as const,
    title: 'Value',
    help: 'The checkbox optionally supports a mixed state in addition to checked and unchecked, following the ARIA checkbox pattern.',
    options: [
      { title: 'Unchecked', name: 'false' },
      { title: 'Checked', name: 'true' },
      { title: 'Indeterminate', name: 'indeterminate' }
    ],
    initialState: 'false' as const
  },
  label: {
    type: 'string' as const,
    title: 'Label',
    initialState: 'Enable notifications'
  },
  help: {
    type: 'string' as const,
    title: 'Help Text',
    initialState: 'You will receive alerts via email.'
  },
  disabled: {
    type: 'boolean' as const,
    title: 'Disabled',
    initialState: false
  },
  padding: {
    type: 'list' as const,
    title: 'Padding',
    help: 'Adds 2px of padding to the checkbox in the given direction.',
    options: listOptions<CheckboxPadding>({
      both: 'Both',
      top: 'Top',
      bottom: 'Bottom'
    }),

    initialState: 'both' as const
  },
  labelPosition: {
    type: 'list' as const,
    title: 'Label Position',
    help: "With 'left' the label comes first and the checkbox sits at the far end of the component, top-aligned. Combine with dots to fill the gap between label and checkbox.",
    options: listOptions<CheckboxLabelPosition>({
      right: 'Right',
      left: 'Left'
    }),
    initialState: 'right' as const
  },
  dots: {
    type: 'boolean' as const,
    title: 'Show Dots',
    initialState: false
  },
  externalErrors: {
    type: 'string' as const,
    title: 'External Error Message',
    initialState: ''
  }
} satisfies PanelConfigFor<typeof CmkCheckbox, 'allowIndeterminate' | 'modelValue'> & {
  value: ListPropDef<'true' | 'false' | 'indeterminate'>
}
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
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import { computed } from 'vue'

import UclCmkCheckboxDev from './UclCmkCheckboxDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkCheckbox,
  'allowIndeterminate' | 'modelValue'
>().createRef(panelConfig)

const checkboxValue = computed<boolean | 'indeterminate'>({
  get: () =>
    propState.value.value === 'indeterminate' ? 'indeterminate' : propState.value.value === 'true',
  set: (newValue) => {
    propState.value.value =
      newValue === 'indeterminate' ? 'indeterminate' : newValue ? 'true' : 'false'
  }
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkCheckbox</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-cmk-checkbox__stack">
        <CmkParagraph>Preceding text</CmkParagraph>
        <CmkCheckbox
          v-model="checkboxValue"
          :allow-indeterminate="true"
          :label="propState.label"
          :help="propState.help"
          :disabled="propState.disabled"
          :padding="propState.padding"
          :label-position="propState.labelPosition"
          :dots="propState.dots"
          :external-errors="propState.externalErrors ? [propState.externalErrors] : []"
        />
        <CmkParagraph>Following text</CmkParagraph>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkCheckboxDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-cmk-checkbox__stack {
  display: flex;
  flex-direction: column;
}
</style>
