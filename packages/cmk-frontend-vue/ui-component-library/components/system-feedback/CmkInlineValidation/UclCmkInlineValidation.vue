<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkInlineValidationCodeExample.vue?raw'

export const panelConfig = {
  validation: {
    type: 'boolean' as const,
    title: 'validation',
    initialState: true
  }
} satisfies PanelConfigFor<typeof CmkInlineValidation>
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

import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkInlineValidation>().createRef(panelConfig)
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
