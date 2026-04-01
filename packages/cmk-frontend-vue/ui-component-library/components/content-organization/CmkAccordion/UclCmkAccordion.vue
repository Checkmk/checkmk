<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type HeadingType } from '@/components/typography/CmkHeading.vue'

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to the accordion header.'
  },
  {
    keys: [['Shift', 'Tab']],
    description:
      'Moves focus to the accordion header from the next focusable element in reverse order.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'Toggles the expansion state of the focused accordion item.'
  }
]
export const codeExample = `<script setup lang="ts">
import { ref } from 'vue'
${'import'} CmkAccordion from '@/components/CmkAccordion/CmkAccordion.vue'
${'import'} CmkAccordionItem from '@/components/CmkAccordion/CmkAccordionItem.vue'
${'import'} CmkAccordionItemStateIndicator from '@/components/CmkAccordion/CmkAccordionItemStateIndicator.vue'
${'import'} CmkIcon from '@/components/CmkIcon'

const openedItems = ref(['item-1'])
<${'/'}script>

<template>
  <CmkAccordion v-model="openedItems" :min-open="1" :max-open="1">

    <CmkAccordionItem value="item-1">
      <template #header>
        <div style="display: flex; align-items: center; gap: 8px;">
          <CmkIcon name="users" />
          <span>Personal Information</span>
          <CmkAccordionItemStateIndicator value="item-1" />
        </div>
      </template>
      <template #content>
        <p>Manage your personal details, email address, and profile settings.</p>
      </template>
    </CmkAccordionItem>

    <CmkAccordionItem value="item-2">
      <template #header>
        <div style="display: flex; align-items: center; gap: 8px;">
          <CmkIcon name="passwords" />
          <span>Security Settings</span>
        </div>
      </template>
      <template #content>
        <p>Update your password, enable 2FA, and manage security keys.</p>
      </template>
    </CmkAccordionItem>

    <CmkAccordionItem value="item-3">
      <template #header>
        <div style="display: flex; align-items: center; gap: 8px;">
          <CmkIcon name="notifications" />
          <span>Notifications</span>
        </div>
      </template>
      <template #content>
        <p>Configure email digests and real-time alert preferences.</p>
      </template>
    </CmkAccordionItem>

  </CmkAccordion>
</template>`
export const panelConfig = {
  minOpen: {
    type: 'number',
    title: 'minOpen',
    help: '0 allows all items to be collapsed, while 1 or more ensures that at least that many items are always expanded.',
    initialState: 1
  },
  maxOpen: {
    type: 'number',
    title: 'maxOpen',
    help: '0 allows unlimited items to be expanded, while 1 restricts to only one item at a time.',
    initialState: 1
  },
  openedItems: {
    type: 'string-array',
    title: 'openedItems',
    initialState: ['item-1'],
    help: 'Type: string[]. IDs must match the value prop of each CmkAccordionItem. In the UCL app, enter one ID per line in the textarea, e.g.:item-1 item-2 item-3'
  }
} satisfies PanelConfig
export const itemPanelConfig = {
  headerAs: {
    type: 'list',
    title: 'headerAs',
    options: [
      { title: 'h1', name: 'h1' },
      { title: 'h2', name: 'h2' },
      { title: 'h3', name: 'h3' },
      { title: 'h4', name: 'h4' }
    ] satisfies Options<NonNullable<HeadingType>>[],
    initialState: 'h3' as NonNullable<HeadingType>,
    help: 'HTML element used to render the accordion item header.'
  },
  disabled: {
    type: 'boolean',
    title: 'disabled',
    initialState: false,
    help: 'Disables all items in the accordion.'
  }
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

import CmkAccordion from '@/components/CmkAccordion/CmkAccordion.vue'
import CmkAccordionItem from '@/components/CmkAccordion/CmkAccordionItem.vue'
import CmkAccordionItemStateIndicator from '@/components/CmkAccordion/CmkAccordionItemStateIndicator.vue'
import CmkIcon from '@/components/CmkIcon'

import UclCmkAccordionDev from './UclCmkAccordionDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))

const itemPropState = ref(createPanelState(itemPanelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkAccordion</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkAccordion
        v-model="propState.openedItems"
        :min-open="propState.minOpen"
        :max-open="propState.maxOpen"
      >
        <CmkAccordionItem
          value="item-1"
          :header-as="itemPropState.headerAs"
          :disabled="itemPropState.disabled"
        >
          <template #header>
            <div style="display: flex; align-items: center; gap: 8px">
              <CmkIcon name="users" />
              <span>Personal Information</span>
              <CmkAccordionItemStateIndicator value="item-1" />
            </div>
          </template>
          <template #content>
            <p>Manage your personal details, email address, and profile settings.</p>
          </template>
        </CmkAccordionItem>

        <CmkAccordionItem
          value="item-2"
          :header-as="itemPropState.headerAs"
          :disabled="itemPropState.disabled"
        >
          <template #header>
            <div style="display: flex; align-items: center; gap: 8px">
              <CmkIcon name="passwords" />
              <span>Security Settings</span>
            </div>
          </template>
          <template #content>
            <p>Update your password, enable 2FA, and manage security keys.</p>
          </template>
        </CmkAccordionItem>

        <CmkAccordionItem
          value="item-3"
          :header-as="itemPropState.headerAs"
          :disabled="itemPropState.disabled"
        >
          <template #header>
            <div style="display: flex; align-items: center; gap: 8px">
              <CmkIcon name="notifications" />
              <span>Notifications</span>
            </div>
          </template>
          <template #content>
            <p>Configure email digests and real-time alert preferences.</p>
          </template>
        </CmkAccordionItem>
      </CmkAccordion>

      <template #properties>
        <UclPropertiesPanel v-model="propState" title="CmkAccordion" :config="panelConfig" />
        <UclPropertiesPanel
          v-model="itemPropState"
          title="CmkAccordionItem"
          :config="itemPanelConfig"
        />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkAccordionDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
