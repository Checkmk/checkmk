<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef, NumberPropDef } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkStateSummaryFigureCodeExample.vue?raw'

export const panelConfig = {
  inState: {
    type: 'number' as const,
    title: 'In state',
    help: 'The number of objects in the selected state and not in downtime.',
    initialState: 3
  },
  total: {
    type: 'number' as const,
    title: 'Total',
    help: 'The number of all objects.',
    initialState: 10
  },
  linked: {
    type: 'boolean' as const,
    title: 'Linked summary',
    help: 'Gives the summary one resolved link, so the summary renders as an anchor.',
    initialState: true
  },
  width: {
    type: 'number' as const,
    title: 'Width (px)',
    help: 'The measured width the frame hands to the figure.',
    initialState: 300
  },
  height: {
    type: 'number' as const,
    title: 'Height (px)',
    initialState: 200
  }
} satisfies PanelConfigFor<typeof CmkStateSummaryFigure, 'value' | 'filters' | 'interactive'> & {
  inState: NumberPropDef
  total: NumberPropDef
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
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import { computed } from 'vue'

import CmkStateSummaryFigure from '@/dashboard/components/figures/CmkStateSummaryFigure.vue'
import type { ResolvedLink, StateSummary } from '@/dashboard/types/widget'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkStateSummaryFigure,
  'value' | 'filters' | 'interactive'
>().createRef(panelConfig)

const LINK: ResolvedLink = {
  title: 'All hosts',
  location: { type: 'views', name: 'searchhost' },
  include_context: true,
  include_time_range: false,
  show_filter_form: false
}

const value = computed<StateSummary>(() => ({
  links: propState.value.linked ? [LINK] : [],
  in_state: {
    count: propState.value.inState,
    link_properties: { links: propState.value.linked ? [{}] : [] }
  },
  total: propState.value.total
}))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkStateSummaryFigure</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-cmk-state-summary-figure__container">
        <CmkStateSummaryFigure
          :value="value"
          :width="Math.max(0, propState.width)"
          :height="Math.max(0, propState.height)"
          :filters="{}"
          :interactive="propState.linked"
        />
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-cmk-state-summary-figure__container {
  display: inline-block;
  border: 1px solid var(--ucl-elements-border-color);
}
</style>
