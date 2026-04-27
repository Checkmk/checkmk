<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

export const codeExample = `<script setup lang="ts">
${'import'} CmkLabel from '@/components/CmkLabel.vue'
${'import'} CmkInput from '@/components/user-input/CmkInput.vue'
${'import'} CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'
<${'/'}script>

<template>
  <CmkLabel>
    Username
    <CmkLabelRequired space="before" />
  </CmkLabel>
  <CmkInput type="text" required />
</template>`
export const panelConfig = {
  show: { type: 'boolean', title: 'Show Required Label', initialState: true },
  space: {
    type: 'list',
    title: 'space',
    options: [
      { title: 'null', name: '' },
      { title: 'Before', name: 'before' },
      { title: 'After', name: 'after' },
      { title: 'Both', name: 'both' }
    ] satisfies Options<'' | 'before' | 'after' | 'both'>[],
    initialState: '' as '' | 'before' | 'after' | 'both'
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

import CmkLabel from '@/components/CmkLabel.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkLabelRequired</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkLabel>
        Example Field Name
        <CmkLabelRequired :show="propState.show" :space="propState.space || null" />
      </CmkLabel>
      <CmkInput type="text" field-size="MEDIUM" />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
