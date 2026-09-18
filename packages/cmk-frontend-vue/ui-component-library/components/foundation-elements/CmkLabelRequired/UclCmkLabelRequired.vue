<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkLabelRequiredCodeExample.vue?raw'

export const panelConfig = {
  show: { type: 'boolean' as const, title: 'Show Required Label', initialState: true },
  space: {
    type: 'list' as const,
    title: 'space',
    options: listOptions<'' | 'before' | 'after' | 'both'>({
      '': 'null',
      before: 'Before',
      after: 'After',
      both: 'Both'
    }),
    initialState: '' as '' | 'before' | 'after' | 'both'
  }
} satisfies PanelConfigFor<typeof CmkLabelRequired>
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
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import useId from 'cmk-ui-library/lib/useId'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkLabelRequired>().createRef(panelConfig)
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
      <CmkInput :id="exampleFieldId" type="text" field-size="medium" />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
