<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkResizeHandleCodeExample.vue?raw'

type ResizeHandleOrientation = 'vertical' | 'horizontal'

export const panelConfig = {
  orientation: {
    type: 'list' as const,
    title: 'orientation',
    options: listOptions<ResizeHandleOrientation>({
      vertical: 'Vertical (resizes columns)',
      horizontal: 'Horizontal (resizes rows)'
    }),
    initialState: 'vertical' as ResizeHandleOrientation,
    help: 'Vertical grips sit on a column divider, horizontal ones on a row divider.'
  }
} satisfies PanelConfigFor<typeof CmkResizeHandle>
</script>

<script setup lang="ts">
import {
  PanelStateCreator,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import CmkResizeHandle from 'cmk-ui-library/components/CmkResizeHandle.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkResizeHandle>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkResizeHandle</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkResizeHandle :orientation="propState.orientation" />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />
  </UclDetailPageLayout>
</template>
