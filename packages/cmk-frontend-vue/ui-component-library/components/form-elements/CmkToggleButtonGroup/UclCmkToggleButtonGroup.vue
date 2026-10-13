<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import {
  type PanelConfig,
  type PanelConfigFor,
  listOptions
} from '@ucl/_ucl/components/detail-page'
import type { ToggleButtonOption } from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'

import codeExample from './UclCmkToggleButtonGroupCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Moves keyboard focus through the individual toggle buttons. While the focus outline is hidden from view, its underlying functionality remains intact.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus in reverse order through the individual toggle buttons.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'Selects the currently focused toggle option.'
  }
]

export const panelConfig = {
  modelValue: {
    type: 'list' as const,
    title: 'Selected Value',
    options: listOptions<string>({
      list: 'list',
      grid: 'grid',
      map: 'map'
    }),
    initialState: 'list' as const
  },
  size: {
    type: 'list' as const,
    title: 'Size',
    options: listOptions<'medium' | 'small'>({
      medium: 'Medium / Large',
      small: 'Small'
    }),
    initialState: 'medium' as const
  },
  variant: {
    type: 'list' as const,
    title: 'Variant',
    options: listOptions<'text' | 'icon'>({
      text: 'Text',
      icon: 'Icon only'
    }),
    initialState: 'text' as const,
    help: 'The icon-only variation is specified for the small size.'
  }
} satisfies PanelConfigFor<typeof CmkToggleButtonGroup, 'options' | 'spacing'> & PanelConfig
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
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import { computed } from 'vue'

defineProps<{ screenshotMode: boolean }>()

const textOptions: ToggleButtonOption[] = [
  { label: 'List View', value: 'list', tooltip: 'Display items in a vertical list' },
  { label: 'Grid View', value: 'grid', tooltip: 'Display items in a grid layout' },
  {
    label: 'Map View',
    value: 'map',
    disabled: true,
    disabledTooltip: 'Requires Checkmk Pro edition'
  }
]

const iconOptions: ToggleButtonOption[] = textOptions.map((option, index) => ({
  ...option,
  icon: (['dash', 'checkmark', 'cancel'] as const)[index]!
}))

const propState = new PanelStateCreator<
  typeof CmkToggleButtonGroup,
  'options' | 'spacing'
>().createRef(panelConfig)

const demoOptions = computed(() => (propState.value.variant === 'icon' ? iconOptions : textOptions))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkToggleButtonGroup</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkToggleButtonGroup
        v-model="propState.modelValue"
        :options="demoOptions"
        :size="propState.size"
        spacing="none"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
