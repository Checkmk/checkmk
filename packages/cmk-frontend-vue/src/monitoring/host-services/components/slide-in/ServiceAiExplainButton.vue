<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { ExplainThisIssueData } from 'cmk-shared-typing/typescript/ai_button'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { ServiceOverview } from '@/monitoring/shared/api/types'

const { _t } = usei18n()

const props = defineProps<{
  overview: ServiceOverview
}>()

const SERVICE_STATES: Record<ServiceOverview['state'], ExplainThisIssueData['service_state']> = {
  OK: 'OK',
  WARN: 'Warning',
  CRIT: 'Critical',
  UNKNOWN: 'Unknown'
}

const HOST_STATES: Record<ServiceOverview['host_state'], ExplainThisIssueData['host_state']> = {
  UP: 'Up',
  DOWN: 'Down',
  UNREACHABLE: 'Unreachable'
}

function explainThis(): void {
  const detail: ExplainThisIssueData = {
    host_name: props.overview.host_name,
    service_name: props.overview.name,
    service_state: SERVICE_STATES[props.overview.state],
    host_state: HOST_STATES[props.overview.host_state]
  }
  document.dispatchEvent(new CustomEvent('cmk-ai-explain-button', { detail }))
}

defineExpose({ explainThis })
</script>

<template>
  <CmkButton
    variant="ai"
    :icon="{ name: 'sparkle' }"
    data-testid="service-ai-explain-button"
    @click="explainThis"
  >
    {{ _t('Explain with AI') }}
  </CmkButton>
</template>
