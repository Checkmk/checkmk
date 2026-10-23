<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import { type CmkSurfaceNoticeVariant } from 'cmk-ui-library/components/CmkSurfaceNotice.vue'

import codeExample from './UclCmkSurfaceNoticeCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to the retry action, when the notice offers one.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'Activates the focused retry action.'
  }
]

export const panelConfig = {
  variant: {
    type: 'list' as const,
    title: 'Variant',
    options: listOptions<CmkSurfaceNoticeVariant>({
      error: 'Error',
      warning: 'Warning',
      loading: 'Loading',
      info: 'Info'
    }),
    initialState: 'error' as const
  },
  message: {
    type: 'string' as const,
    title: 'Message',
    initialState: 'Widget data could not be loaded.'
  },
  description: {
    type: 'string' as const,
    title: 'Description',
    initialState: 'Monitoring data source unavailable'
  },
  retry: { type: 'boolean' as const, title: 'Retry', initialState: true },
  silent: {
    type: 'boolean' as const,
    title: 'Silent',
    initialState: false,
    help: 'Drops the announcing role, for a host that announces one notice for several surfaces.'
  }
} satisfies PanelConfigFor<typeof CmkSurfaceNotice>
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
import CmkSurfaceNotice from 'cmk-ui-library/components/CmkSurfaceNotice.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkSurfaceNotice>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkSurfaceNotice</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkSurfaceNotice
        :variant="propState.variant"
        :message="propState.message"
        :description="propState.description"
        :retry="propState.retry"
        :silent="propState.silent"
        @retry="() => console.log('Retry clicked')"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
