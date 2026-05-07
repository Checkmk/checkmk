<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkTabsCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to the Tab.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the Tab from the next focusable element in reverse order.'
  },
  {
    keys: ['ArrowLeft', 'ArrowRight'],
    description: 'Move focus between tabs.'
  },
  {
    keys: ['Home', 'End'],
    description: 'Move to the first and last tabs respectively.'
  }
]

type TabId = 'tab-1' | 'tab-2' | 'tab-3'

export const panelConfig = {
  modelValue: {
    type: 'list' as const,
    title: 'Active Tab',
    options: [
      { title: 'Search', name: 'tab-1' },
      { title: 'Information', name: 'tab-2' },
      { title: 'Disabled', name: 'tab-3' }
    ] satisfies Options<TabId>[],
    initialState: 'tab-1' as TabId
  }
} satisfies PanelConfigFor<typeof CmkTabs>
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

import CmkIcon from '@/components/CmkIcon'
import CmkTabs, { CmkTab, CmkTabContent } from '@/components/CmkTabs'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkTabs>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkTabs</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkTabs v-model="propState.modelValue">
        <template #tabs>
          <CmkTab id="tab-1"><CmkIcon name="search" /> Search</CmkTab>
          <CmkTab id="tab-2"><CmkIcon name="info-circle" /> Information</CmkTab>
          <CmkTab id="tab-3" :disabled="true"><CmkIcon name="close" /> Disabled</CmkTab>
        </template>

        <template #tab-contents>
          <CmkTabContent id="tab-1">
            <CmkHeading type="h3">Search</CmkHeading>
            <CmkParagraph>Use the search bar to find hosts and services.</CmkParagraph>
          </CmkTabContent>
          <CmkTabContent id="tab-2">
            <CmkHeading type="h3">Information</CmkHeading>
            <CmkParagraph>Detailed system information and status reports.</CmkParagraph>
          </CmkTabContent>
          <CmkTabContent id="tab-3">
            <CmkHeading type="h3">Disabled</CmkHeading>
            <CmkParagraph>This content is not accessible.</CmkParagraph>
          </CmkTabContent>
        </template>
      </CmkTabs>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
