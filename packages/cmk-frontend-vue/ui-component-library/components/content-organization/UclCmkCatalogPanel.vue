<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Moves keyboard focus to header. While the focus outline is hidden from view, its underlying functionality remains intact.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the header from the next focusable element in reverse order.'
  },
  {
    keys: ['Enter', 'Space'],
    description:
      'When the header button is focused, pressing Enter or Space toggles the visibility of the panel content.'
  }
]
export const codeExample = `<script setup lang="ts">
${'import'} CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'
<${'/'}script>

<template>
  <CmkCatalogPanel title="Catalog Panel" variant="default" :open="true">
    This is the collapsible content inside the panel.
  </CmkCatalogPanel>
</template>`

type CatalogPanelVariant = 'default' | 'padded'

export const panelConfig = {
  title: { type: 'string', title: 'Panel Title', initialState: 'Catalog Panel' },
  variant: {
    type: 'list',
    title: 'Variant',
    options: [
      { title: 'Default', name: 'default' },
      { title: 'Padded', name: 'padded' }
    ] satisfies Options<CatalogPanelVariant>[],
    initialState: 'default' as CatalogPanelVariant
  },
  open: { type: 'boolean', title: 'Open', initialState: true }
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

import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'

import UclCmkCatalogPanelDev from './UclCmkCatalogPanelDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkCatalogPanel</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkCatalogPanel
        :key="String(propState.open)"
        :title="propState.title"
        :variant="propState.variant ?? 'default'"
        :open="propState.open"
      >
        This is the collapsible content inside the panel.
      </CmkCatalogPanel>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkCatalogPanelDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
