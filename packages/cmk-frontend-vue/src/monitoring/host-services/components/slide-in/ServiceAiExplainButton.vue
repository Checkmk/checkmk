<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import usei18n from 'cmk-ui-library/lib/i18n'

import { requestAiExplanation } from '@/monitoring/host-services/aiExplain'
import type { ServiceOverview } from '@/monitoring/shared/api/types'

const { _t } = usei18n()

const props = defineProps<{
  overview: ServiceOverview
}>()

function explainThis(): void {
  requestAiExplanation({
    hostName: props.overview.host_name,
    hostState: props.overview.host_state,
    serviceName: props.overview.name,
    serviceState: props.overview.state,
    stale: props.overview.stale
  })
}

defineExpose({ explainThis })
</script>

<template>
  <CmkButton
    variant="ai"
    size="medium"
    :icon="{ name: 'sparkle' }"
    data-testid="service-ai-explain-button"
    @click="explainThis"
  >
    {{ _t('Explain with AI') }}
  </CmkButton>
</template>
