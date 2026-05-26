<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCheckboxCellCodeExample.vue?raw'

export const panelConfig = {
  value: {
    type: 'boolean' as const,
    title: 'value',
    initialState: false,
    help: 'The checked state of the cell. Bound via v-model.'
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import { ref } from 'vue'

import CheckboxCell from '@/monitoring/shared/components/cell/CheckboxCell.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CheckboxCell</UclDetailPageHeader>

    <UclDetailPageComponent>
      <table class="ucl-checkbox-cell__table">
        <tbody>
          <tr>
            <CheckboxCell v-model="propState.value" />
          </tr>
        </tbody>
      </table>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-checkbox-cell__table {
  border-collapse: collapse;
}

/* stylelint-disable selector-pseudo-class-no-unknown */
.ucl-checkbox-cell__table :deep(td) {
  border: 1px solid var(--ux-theme-6);
}
/* stylelint-enable selector-pseudo-class-no-unknown */
</style>
