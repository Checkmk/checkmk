<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkLabelRequiredCodeExample.vue?raw'

export const panelConfig = {
  show: { type: 'boolean' as const, title: 'Show Required Label', initialState: true },
  space: {
    type: 'list' as const,
    title: 'space',
    options: [
      { title: 'null', name: '' },
      { title: 'Before', name: 'before' },
      { title: 'After', name: 'after' },
      { title: 'Both', name: 'both' }
    ] satisfies Options<'' | 'before' | 'after' | 'both'>[],
    initialState: '' as '' | 'before' | 'after' | 'both'
  }
} satisfies PanelConfigFor<typeof CmkLabelRequired>
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

import useId from '@/lib/useId'

import CmkLabel from '@/components/CmkLabel.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
const exampleFieldId = useId()
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkLabelRequired</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkLabel :for="exampleFieldId">
        Example Field Name
        <CmkLabelRequired :show="propState.show" :space="propState.space || null" />
      </CmkLabel>
      <CmkInput :id="exampleFieldId" type="text" field-size="MEDIUM" />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
