<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef, StringPropDef } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkInventoryFigureCodeExample.vue?raw'

export const panelConfig = {
  attribute: {
    type: 'string' as const,
    title: 'Attribute',
    help: 'The inventory attribute as its display hint renders it on the server.',
    initialState: 'Ubuntu 24.04'
  },
  present: {
    type: 'boolean' as const,
    title: 'Attribute present',
    help: 'A host without the attribute shows the not-available text.',
    initialState: true
  },
  linked: {
    type: 'boolean' as const,
    title: 'Linked value',
    help: 'Gives the value one resolved link, so the value renders as an anchor.',
    initialState: true
  },
  width: {
    type: 'number' as const,
    title: 'Width (px)',
    help: 'The measured width the frame hands to the figure. Drag the corner of the preview to change it.',
    initialState: 300
  },
  height: {
    type: 'number' as const,
    title: 'Height (px)',
    initialState: 150
  }
} satisfies PanelConfigFor<typeof CmkInventoryFigure, 'value' | 'filters' | 'interactive'> & {
  attribute: StringPropDef
  present: BoolPropDef
  linked: BoolPropDef
}
</script>

<script setup lang="ts">
import {
  PanelStateCreator,
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel,
  UclResizablePreview
} from '@ucl/_ucl/components/detail-page'
import { computed } from 'vue'

import CmkInventoryFigure from '@/dashboard/components/figures/CmkInventoryFigure.vue'
import type { InventoryAttribute, ResolvedLink } from '@/dashboard/types/widget'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkInventoryFigure,
  'value' | 'filters' | 'interactive'
>().createRef(panelConfig)

const LINK: ResolvedLink = {
  title: 'Inventory of host',
  location: { type: 'views', name: 'inv_host', owner: null },
  include_context: false,
  include_time_range: false,
  show_filter_form: false
}

const value = computed<InventoryAttribute>(() => ({
  links: propState.value.linked ? [LINK] : [],
  link_properties: { links: propState.value.linked ? [{}] : [] },
  value: propState.value.present ? propState.value.attribute : null
}))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkInventoryFigure</UclDetailPageHeader>

    <UclDetailPageComponent>
      <UclResizablePreview v-model:width="propState.width" v-model:height="propState.height">
        <CmkInventoryFigure
          :value="value"
          :width="Math.max(0, propState.width)"
          :height="Math.max(0, propState.height)"
          :filters="{}"
          :interactive="propState.linked"
        />
      </UclResizablePreview>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
