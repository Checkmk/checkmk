<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import codeExample from './UclCmkErrorBoundaryCodeExample.vue?raw'

const CRASH_REPORT_IDENT = '9f2a6c60-9d3e-11f0-9c1a-0242ac110002'
const CRASH_REPORT_URL = `crash.py?component=javascript&ident=${CRASH_REPORT_IDENT}`

const CRASH_REPORT_STATES: Record<string, CrashReportState> = {
  none: { status: 'none' },
  storing: { status: 'storing' },
  stored: { status: 'stored', url: CRASH_REPORT_URL },
  failed: { status: 'failed' }
}

export const panelConfig = {
  error: { type: 'boolean' as const, title: 'error', initialState: false },
  crashReport: {
    type: 'list' as const,
    title: 'crashReport',
    help: 'State of the crash report the caught error is stored as. Only shown while error is set.',
    options: Object.keys(CRASH_REPORT_STATES).map((name) => ({ title: name, name })),
    initialState: 'none'
  }
} satisfies PanelConfig
export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to the error.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the previous focusable element in reverse order.'
  },
  {
    keys: ['Enter', 'Space'],
    description:
      'When focused on the error message, pressing Enter or Space will trigger any available details to be expanded.'
  }
]
</script>

<script setup lang="ts">
import {
  type PanelConfig,
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageDeveloperPlayground,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import { useMswWorker } from '@ucl/_ucl/composables/useMswWorker'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import {
  type CrashReportState,
  useCmkErrorBoundary
} from 'cmk-ui-library/components/CmkErrorBoundary'
import { HttpResponse, http } from 'msw'
import { ref, watch } from 'vue'

import UclCmkErrorBoundaryDev from './UclCmkErrorBoundaryDev.vue'

defineProps<{ screenshotMode: boolean }>()

// eslint-disable-next-line @typescript-eslint/naming-convention
const { CmkErrorBoundary, error, crashReport } = useCmkErrorBoundary()

useMswWorker([
  http.post(/\/domain-types\/javascript_crash_report\/collections\/all$/, () =>
    HttpResponse.json(
      {
        domainType: 'javascript_crash_report',
        id: CRASH_REPORT_IDENT,
        title: 'Error: Something unexpected happened in the component tree.',
        links: [],
        extensions: { crash_type: 'javascript', crash_report_url: CRASH_REPORT_URL }
      },
      { status: 201 }
    )
  )
])

// We're not using PanelStateCreator here as CmkErrorBoundary doesn't follow the usual pattern.
const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

watch(
  propState,
  ({ error: hasError, crashReport: crashReportState }) => {
    error.value = hasError
      ? new Error('Something unexpected happened in the component tree.')
      : null
    crashReport.value = CRASH_REPORT_STATES[crashReportState] ?? { status: 'none' }
  },
  { deep: true }
)

function throwError() {
  throw new Error('Something unexpected happened in the component tree.')
}
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkErrorBoundary</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkErrorBoundary>
        <CmkButton @click="throwError()">Throw error</CmkButton>
      </CmkErrorBoundary>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkErrorBoundaryDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
