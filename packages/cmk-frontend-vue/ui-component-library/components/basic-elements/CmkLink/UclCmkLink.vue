<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

type TargetOption = '_blank' | 'main' | ''

export const panelConfig = {
  href: {
    type: 'string' as const,
    title: 'href',
    initialState: 'https://docs.checkmk.com'
  },
  target: {
    type: 'list' as const,
    title: 'target',
    options: [
      { title: 'None (default)', name: '' },
      { title: '_blank (new tab)', name: '_blank' },
      { title: 'main iframe', name: 'main' }
    ] satisfies Options<TargetOption>[],
    initialState: '' as TargetOption
  }
} satisfies PanelConfigFor<typeof CmkLink>
</script>

<script setup lang="ts">
import {
  PanelStateCreator,
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageDeveloperPlayground,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'

import CmkLink from '@/components/CmkLink.vue'

import codeExampleCmkLink from './UclCmkLinkCodeExample.vue?raw'
import UclCmkLinkDev from './UclCmkLinkDev.vue'

defineProps<{ screenshotMode: boolean }>()

const a11yDataCmkLink = [
  {
    keys: ['Tab'],
    description:
      'Moves keyboard focus to the link. The link is focusable and acts as a standard hyperlink.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the link from the next focusable element in reverse order.'
  },
  {
    keys: ['Enter'],
    description: 'Activates the link, following the URL.'
  }
]

const propState = new PanelStateCreator<typeof CmkLink>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkLink</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkLink :href="propState.href" :target="propState.target || undefined">
        This can be text, icons and/or other components
      </CmkLink>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExampleCmkLink" />

    <UclDetailPageAccessibility :data="a11yDataCmkLink" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkLinkDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
