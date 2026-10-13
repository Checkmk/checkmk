<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import { type LabelProps } from 'cmk-ui-library/components/CmkLabel.vue'

import codeExample from './UclCmkLabelCodeExample.vue?raw'

export const panelConfig = {
  variant: {
    type: 'list' as const,
    title: 'Variant',
    options: listOptions<LabelProps['variant']>({
      default: 'Default',
      title: 'Title',
      subtitle: 'Subtitle'
    }),
    initialState: 'default' as const
  },
  dots: {
    type: 'boolean' as const,
    title: 'Dots',
    help: 'Append dots to label, limited to some hardcoded amount.',
    initialState: false
  },
  grow: {
    type: 'boolean' as const,
    title: 'Grow',
    help: 'Grow to fill available space in a surrounding flex container; with dots the dots expand accordingly.',
    initialState: false
  },
  cursor: {
    type: 'list' as const,
    title: 'Cursor',
    options: listOptions<LabelProps['cursor']>({
      default: 'Default',
      inherit: 'Inherit',
      pointer: 'Pointer'
    }),
    initialState: 'default' as const
  },
  help: {
    type: 'string' as const,
    title: 'Help Text',
    initialState: 'Example help text'
  }
} satisfies PanelConfigFor<typeof CmkLabel, 'for'>
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

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkLabel, 'for'>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkLabel</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkLabel
        :variant="propState.variant"
        :dots="propState.dots"
        :grow="propState.grow"
        :cursor="propState.cursor"
        :help="propState.help"
      >
        Form Field
      </CmkLabel>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
