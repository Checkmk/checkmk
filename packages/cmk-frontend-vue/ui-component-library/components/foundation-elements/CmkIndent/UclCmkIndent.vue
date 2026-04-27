<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

export const codeExample = `<script setup lang="ts">
${'import'} CmkIndent from '@/components/CmkIndent.vue'
<${'/'}script>

<template>
  <p>Top Level Content</p>
  <CmkIndent>
    <p>First Level Indentation</p>
    <CmkIndent error>
      <p>Second Level Indentation</p>
    </CmkIndent>
  </CmkIndent>
</template>`
export const panelConfig = {
  indent: { type: 'boolean', title: 'Enable Indent', initialState: true },
  error: { type: 'boolean', title: 'Error State', initialState: false }
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

import CmkIndent from '@/components/CmkIndent.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkIndent</UclDetailPageHeader>

    <UclDetailPageComponent>
      <p>Top Level Content</p>

      <CmkIndent :indent="propState.indent" :error="propState.error">
        <p>First Level Indentation</p>

        <CmkIndent :indent="propState.indent" :error="propState.error">
          <p>Second Level Indentation</p>
        </CmkIndent>
      </CmkIndent>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
