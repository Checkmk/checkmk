<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef, ListPropDef, NumberPropDef } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkGaugeFigureCodeExample.vue?raw'

type Unit = 'percent' | 'bytes' | 'count'

type Status = 'none' | 'ok' | 'warning_text' | 'critical_background' | 'pending'

type History = 'none' | 'narrow' | 'wide'

export const panelConfig = {
  current: {
    type: 'number' as const,
    title: 'Current value',
    help: 'The value the server reports, in the unit below.',
    initialState: 42
  },
  hasValue: {
    type: 'boolean' as const,
    title: 'Service reports a value',
    help: 'Without a value, the gauge draws only its span and the range labels.',
    initialState: true
  },
  unit: {
    type: 'list' as const,
    title: 'Unit',
    help: 'The unit format the server sends with the value.',
    options: listOptions<Unit>({ percent: 'Percent', bytes: 'Bytes', count: 'Plain count' }),
    initialState: 'percent' as const
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
  status: {
    type: 'list' as const,
    title: 'Status',
    help: 'The service status, as the widget configuration and the service state decide it.',
    options: listOptions<Status>({
      none: 'No status',
      ok: 'OK, as a label',
      warning_text: 'Warning, as a label',
      critical_background: 'Critical, with a tinted background',
      pending: 'Pending'
    }),
    initialState: 'warning_text' as const
  },
  history: {
    type: 'list' as const,
    title: 'History',
    help: 'The samples of the time range. The histogram shows from eleven values on, the current value included.',
    options: listOptions<History>({
      none: 'Current value only',
      narrow: 'Values close to the current value',
      wide: 'Values over the whole range'
    }),
    initialState: 'wide' as const
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
    initialState: 200
  }
} satisfies PanelConfigFor<typeof CmkGaugeFigure, 'value' | 'filters' | 'interactive'> & {
  current: NumberPropDef
  hasValue: BoolPropDef
  unit: ListPropDef<Unit>
  minimum: NumberPropDef
  maximum: NumberPropDef
  status: ListPropDef<Status>
  history: ListPropDef<History>
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

import CmkGaugeFigure from '@/dashboard/components/figures/CmkGaugeFigure.vue'
import type { Gauge, GaugeStatus, ResolvedLink } from '@/dashboard/types/widget'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkGaugeFigure,
  'value' | 'filters' | 'interactive'
>().createRef(panelConfig)

const UNIT_FORMAT: Record<Unit, Gauge['unit_format']> = {
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

const STATUS: Record<Status, GaugeStatus | null> = {
  none: null,
  ok: { state: 'OK', has_been_checked: true, tint_background: false },
  warning_text: { state: 'WARNING', has_been_checked: true, tint_background: false },
  critical_background: { state: 'CRITICAL', has_been_checked: true, tint_background: true },
  pending: { state: 'OK', has_been_checked: false, tint_background: false }
}

const LINK: ResolvedLink = {
  title: 'Service',
  location: { type: 'views', name: 'service', owner: null },
  include_context: false,
  include_time_range: false,
  show_filter_form: false
}

function historyValues(history: History, current: number, minimum: number, maximum: number) {
  const span = maximum - minimum
  switch (history) {
    case 'none':
      return []
    case 'narrow':
      return Array.from({ length: 60 }, (_, index) => current + span * 0.05 * Math.sin(index))
    case 'wide':
      return Array.from(
        { length: 120 },
        (_, index) => minimum + span * (0.5 + 0.45 * Math.sin(index / 7))
      )
  }
}

const value = computed<Gauge>(() => {
  const { current, minimum, maximum } = propState.value
  return {
    links: propState.value.linked ? [LINK] : [],
    link_properties: { links: propState.value.linked ? [{}] : [] },
    value: propState.value.hasValue ? current : null,
    unit_format: UNIT_FORMAT[propState.value.unit],
    range: { minimum, maximum },
    samples: historyValues(propState.value.history, current, minimum, maximum).map(
      (sample, index) => ({
        timestamp: new Date(Date.UTC(2026, 0, 1, 0, index)).toISOString(),
        value: sample
      })
    ),
    status: STATUS[propState.value.status]
  }
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkGaugeFigure</UclDetailPageHeader>

    <UclDetailPageComponent>
      <UclResizablePreview v-model:width="propState.width" v-model:height="propState.height">
        <CmkGaugeFigure
          v-if="propState.minimum < propState.maximum"
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
