<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

export const panelConfig = {
  error: { type: 'boolean', title: 'error', initialState: false }
} satisfies PanelConfig
export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to the error.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the previous focusable element in reverse order.'
  },
  {
    keys: ['Enter', 'Space'],
    description:
      'When focused on the error message, pressing Enter or Space will trigger any available details to be expanded.'
  }
]
export const codeExample = `<script setup lang="ts">
${'import'} { useCmkErrorBoundary } from '@/components/CmkErrorBoundary'

// eslint-disable-next-line @typescript-eslint/naming-convention
const { CmkErrorBoundary } = useCmkErrorBoundary()

function throwError() {
  throw new Error('Something went wrong.')
}
<${'/'}script>

<template>
  <CmkErrorBoundary>
    <button @click="throwError()">Throw error</button>
  </CmkErrorBoundary>
</template>`
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
import { ref, watch } from 'vue'

import { useCmkErrorBoundary } from '@/components/CmkErrorBoundary'

import UclCmkErrorBoundaryDev from './UclCmkErrorBoundaryDev.vue'

defineProps<{ screenshotMode: boolean }>()

// eslint-disable-next-line @typescript-eslint/naming-convention
const { CmkErrorBoundary, error } = useCmkErrorBoundary()

const propState = ref(createPanelState(panelConfig))

watch(
  () => propState.value.error,
  (hasError) => {
    error.value = hasError
      ? new Error('Something unexpected happened in the component tree.')
      : null
  }
)

function throwError() {
  throw new Error('Something unexpected happened in the component tree.')
}
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkErrorBoundary</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkErrorBoundary>
        <button @click="throwError()">Throw error</button>
      </CmkErrorBoundary>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkErrorBoundaryDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
