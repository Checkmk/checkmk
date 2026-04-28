<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkWizardCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to the next wizard button or interactive element.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus in reverse order through the wizard buttons and interactive elements.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'Activates the focused Previous or Next button.'
  }
]

export const panelConfig = {
  mode: {
    type: 'list',
    title: 'Wizard Mode',
    options: [
      { title: 'Guided (Step-by-Step)', name: 'guided' },
      { title: 'Overview (Stacked)', name: 'overview' }
    ] satisfies Options<'guided' | 'overview'>[],
    initialState: 'guided' as 'guided' | 'overview'
  },
  currentStep: {
    type: 'list',
    title: 'Current Step',
    options: [
      { title: 'Step 1', name: '1' },
      { title: 'Step 2', name: '2' },
      { title: 'Step 3', name: '3' }
    ],
    initialState: '1'
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
import { computed, ref } from 'vue'

import CmkWizard, {
  CmkWizardButton,
  CmkWizardModeToggle,
  CmkWizardStep
} from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import UclCmkWizardDev from './UclCmkWizardDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))

const wizardStep = computed({
  get: () => Number(propState.value.currentStep as string),
  set: (val: number) => {
    propState.value.currentStep = String(val)
  }
})

const wizardMode = computed({
  get: () => propState.value.mode as 'guided' | 'overview',
  set: (val: 'guided' | 'overview') => {
    propState.value.mode = val
  }
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkWizard</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div style="width: 100%; max-width: 800px">
        <div style="margin-bottom: var(--dimension-4)">
          <CmkWizardModeToggle v-model="wizardMode" />
        </div>

        <CmkWizard v-model="wizardStep" :mode="wizardMode">
          <CmkWizardStep :index="1" :is-completed="() => wizardStep > 1">
            <template #header><CmkHeading type="h3">Step 1: Introduction</CmkHeading></template>
            <template #content>
              <CmkParagraph
                >Welcome to the setup wizard. Please provide your initial details.</CmkParagraph
              >
            </template>
            <template #actions>
              <CmkWizardButton type="next" />
            </template>
          </CmkWizardStep>

          <CmkWizardStep :index="2" :is-completed="() => wizardStep > 2">
            <template #header><CmkHeading type="h3">Step 2: Configuration</CmkHeading></template>
            <template #content>
              <CmkParagraph>Adjust the parameters for your monitoring instance here.</CmkParagraph>
            </template>
            <template #actions>
              <CmkWizardButton type="previous" />
              <CmkWizardButton type="next" />
            </template>
          </CmkWizardStep>

          <CmkWizardStep :index="3" :is-completed="() => wizardStep > 3">
            <template #header><CmkHeading type="h3">Step 3: Review</CmkHeading></template>
            <template #content>
              <CmkParagraph
                >Verify that all settings are correct before finishing the process.</CmkParagraph
              >
            </template>
            <template #actions>
              <CmkWizardButton type="previous" />
              <CmkWizardButton type="next" label="Complete Setup" />
            </template>
          </CmkWizardStep>
        </CmkWizard>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
    <UclDetailPageDeveloperPlayground>
      <UclCmkWizardDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
