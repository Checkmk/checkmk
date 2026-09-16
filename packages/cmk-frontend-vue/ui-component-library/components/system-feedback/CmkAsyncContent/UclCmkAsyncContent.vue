<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import type { PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef, StringPropDef } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkAsyncContentCodeExample.vue?raw'

type OmittedProps = 'component' | 'load' | 'skeleton' | 'props'
type CmkAsyncContentDemoProps = PanelConfigFor<typeof CmkAsyncContent, OmittedProps> & {
  label: StringPropDef
  mounted: BoolPropDef
  slowLoad: BoolPropDef
  failLoad: BoolPropDef
}

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to the Retry button offered after a failed load.'
  }
]

export const panelConfig = {
  mounted: {
    type: 'boolean' as const,
    title: 'Mounted',
    help: 'The body loads on mount and for as long as it is mounted, so this is also what starts a load over.',
    initialState: true
  },
  label: { type: 'string' as const, title: 'Body Label', initialState: 'Overview' },
  slowLoad: {
    type: 'boolean' as const,
    title: 'Simulate Slow Load',
    help: 'Delays the loader, so the body shows the loading indicator it stands in for.',
    initialState: false
  },
  failLoad: {
    type: 'boolean' as const,
    title: 'Simulate Failing Load',
    help: 'Rejects the loader, so the body shows the error and its Retry.',
    initialState: false
  }
} satisfies CmkAsyncContentDemoProps
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
import CmkAsyncContent from 'cmk-ui-library/components/CmkAsyncContent'
import { markRaw } from 'vue'

import CmkSlideInTabbedDemoTab from '../../content-organization/CmkSlideInTabbed/CmkSlideInTabbedDemoTab.vue'

const demoBody = markRaw(CmkSlideInTabbedDemoTab)

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkAsyncContent, OmittedProps>().createRef(
  panelConfig
)

function demoLoad(): Promise<{ loadedAt: string }> {
  if (propState.value.failLoad) {
    return Promise.reject(new Error('The demo loader was told to fail.'))
  }
  const payload = { loadedAt: new Date().toLocaleTimeString() }
  if (!propState.value.slowLoad) {
    return Promise.resolve(payload)
  }
  return new Promise((resolve) => {
    setTimeout(() => resolve(payload), 1200)
  })
}
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkAsyncContent</UclDetailPageHeader>

    <UclDetailPageComponent>
      <!-- Keyed on what a load depends on, so switching a control mounts a new
           body and the demo reads the way a container's would. -->
      <div class="ucl-cmk-async-content__frame">
        <CmkAsyncContent
          v-if="propState.mounted"
          :key="`${propState.slowLoad}-${propState.failLoad}-${propState.label}`"
          :component="demoBody"
          :props="{ label: propState.label }"
          :load="demoLoad"
        />
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>

<style scoped>
/* Bordered, so what the body takes up is visible even while it is a spinner. */
.ucl-cmk-async-content__frame {
  min-height: 120px;
  padding: var(--spacing);
  border: 1px solid var(--ucl-elements-border-color);
}
</style>
