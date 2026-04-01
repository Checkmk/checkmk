<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

export const codeExample = `<script setup lang="ts">
import { ref } from 'vue'

${'import'} CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'

const formErrors = ref<string[]>([
  'This is an inline validation error message.',
  'A secondary validation condition also failed.'
])
<${'/'}script>

<template>
  <CmkInlineValidation :validation="formErrors" />
</template>`
export const panelConfig = {
  validation: {
    type: 'boolean',
    title: 'validation',
    initialState: true
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel,
  createPanelState
} from '@ucl/_ucl/components/detail-page'
import { ref } from 'vue'

import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkInlineValidation</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkInlineValidation
        :validation="
          propState.validation
            ? [
                'This is an inline validation error message.',
                'A secondary validation condition also failed.'
              ]
            : undefined
        "
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
