<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef, ListPropDef, NumberPropDef } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkBarplotFigureCodeExample.vue?raw'

type Unit = 'percent' | 'bytes' | 'count'

export const panelConfig = {
  hosts: {
    type: 'number' as const,
    title: 'Hosts',
    help: 'The number of bars. With fewer than 12 pixels per bar, the host labels hide.',
    initialState: 5
  },
  unit: {
    type: 'list' as const,
    title: 'Unit',
    help: 'The unit format the server sends with the bars.',
    options: listOptions<Unit>({ percent: 'Percent', bytes: 'Bytes', count: 'Plain count' }),
    initialState: 'percent' as const
  },
  fixedRange: {
    type: 'boolean' as const,
    title: 'Fixed range',
    help: 'Without a fixed range, the axis runs from 0 to the largest value.',
    initialState: false
  },
  minimum: {
    type: 'number' as const,
    title: 'Range minimum',
    initialState: 0
  },
  maximum: {
    type: 'number' as const,
    title: 'Range maximum',
    initialState: 100
  },
  linked: {
    type: 'boolean' as const,
    title: 'Linked bars',
    help: 'Gives the widget one resolved link, so every bar renders as an anchor.',
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
    initialState: 200
  }
} satisfies PanelConfigFor<typeof CmkBarplotFigure, 'value' | 'filters'> & {
  hosts: NumberPropDef
  unit: ListPropDef<Unit>
  fixedRange: BoolPropDef
  minimum: NumberPropDef
  maximum: NumberPropDef
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

import CmkBarplotFigure from '@/dashboard/components/figures/CmkBarplotFigure.vue'
import type { Barplot, ResolvedLink } from '@/dashboard/types/widget'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkBarplotFigure, 'value' | 'filters'>().createRef(
  panelConfig
)

const UNIT_FORMAT: Record<Unit, Barplot['unit_format']> = {
  percent: {
    notation: 'decimal',
    symbol: '%',
    precision: { type: 'auto', digits: 2 },
    convertible: false
  },
  bytes: {
    notation: 'iec',
    symbol: 'B',
    precision: { type: 'auto', digits: 2 },
    convertible: false
  },
  count: {
    notation: 'decimal',
    symbol: '',
    precision: { type: 'auto', digits: 2 },
    convertible: false
  }
}

const SCALE: Record<Unit, number> = { percent: 100, bytes: 2 ** 30, count: 1000 }

const LINK: ResolvedLink = {
  title: 'Service',
  location: { type: 'views', name: 'service', owner: null },
  include_context: false,
  include_time_range: false,
  show_filter_form: false
}

const value = computed<Barplot>(() => {
  const { hosts, unit, linked, fixedRange, minimum, maximum } = propState.value
  return {
    links: linked ? [LINK] : [],
    unit_format: UNIT_FORMAT[unit],
    range: fixedRange ? { minimum, maximum } : null,
    bars: Array.from({ length: Math.max(0, hosts) }, (_, index) => ({
      site_id: 'heute',
      host_name: `host-${index + 1}`,
      service_description: 'CPU utilization',
      value: SCALE[unit] * (0.5 + 0.45 * Math.sin(index)),
      link_properties: { links: linked ? [{}] : [] }
    }))
  }
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkBarplotFigure</UclDetailPageHeader>

    <UclDetailPageComponent>
      <UclResizablePreview v-model:width="propState.width" v-model:height="propState.height">
        <CmkBarplotFigure
          :value="value"
          :width="Math.max(0, propState.width)"
          :height="Math.max(0, propState.height)"
          :filters="{}"
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
