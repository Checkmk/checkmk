<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef, StringPropDef } from '@ucl/_ucl/types/prop-def'
import type { SlideInVariants } from 'cmk-ui-library/components/CmkSlideIn'

import codeExample from './UclCmkSlideInTabbedCodeExample.vue?raw'

type OmittedProps = 'tabs' | 'header' | 'defaultTabId' | 'activeTabId' | 'overrideActive'
type CmkSlideInTabbedDemoProps = PanelConfigFor<typeof CmkSlideInTabbed, OmittedProps> & {
  title: StringPropDef
  showCloseButton: BoolPropDef
  slowLoad: BoolPropDef
}

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus through the focusable elements within the slide-in.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus in reverse order through the focusable elements.'
  },
  {
    keys: ['ArrowLeft', 'ArrowRight'],
    description: 'Move focus between the tab triggers.'
  },
  {
    keys: ['Home', 'End'],
    description: 'Move to the first and last tab respectively.'
  },
  {
    keys: ['Escape'],
    description: 'Closes the slide-in.'
  }
]

export const panelConfig = {
  open: { type: 'boolean' as const, title: 'Is Open', initialState: false },
  title: { type: 'string' as const, title: 'Header Title', initialState: 'Host overview' },
  showCloseButton: { type: 'boolean' as const, title: 'Show Close Button', initialState: true },
  slowLoad: { type: 'boolean' as const, title: 'Simulate Slow Load', initialState: false },
  size: {
    type: 'list' as const,
    title: 'Size',
    options: [
      { title: 'Medium', name: 'medium' },
      { title: 'Small', name: 'small' }
    ] satisfies Options<SlideInVariants['size']>[],
    initialState: 'medium' as const
  },
  borderColor: {
    type: 'list' as const,
    title: 'Border Color',
    options: [
      { title: 'Default', name: 'default' },
      { title: 'Purple', name: 'purple' }
    ] satisfies Options<SlideInVariants['borderColor']>[],
    initialState: 'default' as const
  }
} satisfies CmkSlideInTabbedDemoProps
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
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkSlideInTabbed, { type SlideInTab } from 'cmk-ui-library/components/CmkSlideInTabbed'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import { computed, markRaw } from 'vue'

import CmkSlideInTabbedDemoTab from './CmkSlideInTabbedDemoTab.vue'

const demoTab = markRaw(CmkSlideInTabbedDemoTab)

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkSlideInTabbed, OmittedProps>().createRef(
  panelConfig
)

function demoLoad(): Promise<{ loadedAt: string }> {
  const payload = { loadedAt: new Date().toLocaleTimeString() }
  if (!propState.value.slowLoad) {
    return Promise.resolve(payload)
  }
  return new Promise((resolve) => {
    setTimeout(() => resolve(payload), 1200)
  })
}

const tabs = computed<SlideInTab[]>(() => [
  {
    id: 'overview',
    title: 'Overview',
    component: demoTab,
    props: { label: 'Overview' },
    load: demoLoad
  },
  {
    id: 'details',
    title: 'Details',
    component: demoTab,
    props: { label: 'Details' },
    load: demoLoad
  },
  {
    id: 'history',
    title: 'History',
    component: demoTab,
    props: { label: 'History' },
    load: demoLoad
  }
])

const headerConfig = computed(() => ({
  title: propState.value.title,
  closeButton: propState.value.showCloseButton
}))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkSlideInTabbed</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkButton @click="propState.open = true">Open tabbed slide-in</CmkButton>

      <CmkSlideInTabbed
        :open="propState.open"
        :tabs="tabs"
        :header="headerConfig"
        :size="propState.size"
        :border-color="propState.borderColor"
        @close="propState.open = false"
      >
        <template #above-tabs>
          <CmkParagraph>
            This area is a dedicated slot above the tabs, e.g. for a host header or summary.
          </CmkParagraph>
        </template>
      </CmkSlideInTabbed>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
