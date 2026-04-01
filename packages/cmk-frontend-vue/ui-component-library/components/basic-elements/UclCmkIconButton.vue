<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import {
  type PanelConfig,
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

import type { CmkIconVariants, IconSizeNames, SimpleIcons } from '@/components/CmkIcon'
import CmkIconButton from '@/components/CmkIconButton.vue'

import UclCmkIconButtonDev from './UclCmkIconButtonDev.vue'

defineProps<{ screenshotMode: boolean }>()

const a11yDataCmkIconButton = [
  {
    keys: ['Tab'],
    description:
      'Moves keyboard focus to the button. While the focus outline is hidden from view, its underlying functionality remains intact.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the button from the next focusable element in reverse order.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'Activates the button and emits the click event.'
  }
]

const codeExampleCmkIconButton = `<script setup lang="ts">
${'import'} CmkIconButton from '@/components/CmkIconButton.vue'

const handleClick = () => {
  console.log('Button clicked!')
}
<${'/'}script>

<template>
  <CmkIconButton
    name="main-help"
    size="medium"
    title="Get Help"
    @click="handleClick"
  />
</template>`

const panelConfig = {
  name: { type: 'string', title: 'Icon Name', initialState: 'main-help' },
  variant: {
    type: 'list',
    title: 'Variant',
    options: [
      { title: 'Plain', name: 'plain' },
      { title: 'Inline (with margin)', name: 'inline' }
    ],
    initialState: 'plain'
  },
  size: {
    type: 'list',
    title: 'Size',
    options: [
      { title: 'XX-Small', name: 'xxsmall' },
      { title: 'X-Small', name: 'xsmall' },
      { title: 'Small', name: 'small' },
      { title: 'Medium', name: 'medium' },
      { title: 'Large', name: 'large' },
      { title: 'X-Large', name: 'xlarge' },
      { title: 'XX-Large', name: 'xxlarge' },
      { title: 'XXX-Large', name: 'xxxlarge' }
    ],
    initialState: 'medium'
  },
  title: { type: 'string', title: 'Title (Tooltip)', initialState: 'Get Help' },
  rotate: { type: 'number', title: 'Rotation (Degrees)', initialState: 0 }
} satisfies PanelConfig

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkIconButton</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkIconButton
        :name="propState.name as SimpleIcons"
        :variant="propState.variant as CmkIconVariants['variant']"
        :size="propState.size as IconSizeNames"
        :title="propState.title"
        :rotate="propState.rotate"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExampleCmkIconButton" />

    <UclDetailPageAccessibility :data="a11yDataCmkIconButton" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkIconButtonDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
