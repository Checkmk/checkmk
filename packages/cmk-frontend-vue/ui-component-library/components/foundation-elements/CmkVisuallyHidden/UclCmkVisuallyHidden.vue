<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkVisuallyHiddenCodeExample.vue?raw'

export const panelConfig = {
  text: {
    type: 'string' as const,
    title: 'Text',
    initialState: 'Screen reader message'
  },
  live: {
    type: 'list' as const,
    title: 'Live region',
    options: [
      { title: 'Off (static label)', name: 'off' },
      { title: 'Polite', name: 'polite' },
      { title: 'Assertive', name: 'assertive' }
    ] satisfies Options<'off' | 'polite' | 'assertive'>[],
    help: 'Polite/assertive turn the element into a live region that announces changes to its text.',
    initialState: 'off' as const
  }
} satisfies PanelConfigFor<typeof CmkVisuallyHidden, 'id'>
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

import CmkVisuallyHidden from '@/components/CmkVisuallyHidden.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkVisuallyHidden, 'id'>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkVisuallyHidden</UclDetailPageHeader>

    <UclDetailPageComponent>
      <p>
        This component renders nothing visible — its text lives only in the accessibility tree, for
        screen-reader-only labels and live-region announcements. Inspect the DOM or use a screen
        reader to observe it. Current text: <code>{{ propState.text }}</code>
      </p>
      <CmkVisuallyHidden :text="propState.text" :live="propState.live" />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
