<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import type { CmkSpaceVariants } from '@/components/CmkSpace.vue'

import codeExample from './UclCmkSpaceCodeExample.vue?raw'

export const panelConfig = {
  size: {
    type: 'list' as const,
    title: 'Size',
    options: [
      { title: 'Medium', name: 'medium' },
      { title: 'Small', name: 'small' }
    ] satisfies Options<CmkSpaceVariants['size']>[],
    initialState: 'medium' as const
  }
} satisfies PanelConfigFor<typeof CmkSpace, 'direction'>
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

import CmkButton from '@/components/CmkButton'
import CmkSpace from '@/components/CmkSpace.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkSpace, 'direction'>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkSpace</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-cmk-space">
        <div class="ucl-cmk-space__example">
          <span class="ucl-cmk-space__label">Horizontal Direction</span>
          <div class="ucl-cmk-space__row">
            <CmkButton variant="secondary">First Element</CmkButton>
            <CmkSpace direction="horizontal" :size="propState.size" />
            <CmkButton variant="primary">Second Element</CmkButton>
          </div>
        </div>

        <div class="ucl-cmk-space__example">
          <span class="ucl-cmk-space__label">Vertical Direction</span>
          <div class="ucl-cmk-space__column">
            <CmkButton variant="secondary">First Element</CmkButton>
            <CmkSpace direction="vertical" :size="propState.size" />
            <CmkButton variant="primary">Second Element</CmkButton>
          </div>
        </div>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-cmk-space {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-10);
  align-items: flex-start;
}

.ucl-cmk-space__example {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.ucl-cmk-space__label {
  font-size: var(--font-size-small, 0.75rem);
  opacity: 0.6;
}

.ucl-cmk-space__row {
  display: flex;
  flex-direction: row;
  align-items: center;
}

.ucl-cmk-space__column {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
</style>
