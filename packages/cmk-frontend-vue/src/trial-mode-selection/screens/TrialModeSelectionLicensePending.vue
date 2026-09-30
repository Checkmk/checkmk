<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

import TrialModeSelectionTrialStatus from '../components/TrialModeSelectionTrialStatus.vue'

const { trialEndTimestamp, trialLengthDays, freeServicesLimit, saving } = defineProps<{
  /** When the trial runs out, as a timestamp. */
  trialEndTimestamp: number
  trialLengthDays: number
  /** Services the free edition monitors once the trial has ended. */
  freeServicesLimit: number
  saving: boolean
}>()

const emit = defineEmits<{
  back: []
  startMonitoring: []
}>()

const { _t } = usei18n()
</script>

<template>
  <TrialModeSelectionTrialStatus
    :badge-label="_t('License activation pending')"
    badge-color="success"
    :trial-end-timestamp="trialEndTimestamp"
    :trial-length-days="trialLengthDays"
    :saving="saving"
    @back="emit('back')"
    @start-monitoring="emit('startMonitoring')"
  >
    {{
      _t(
        "License verification postponed. The site keeps full features for %{days} days from site creation. Verify your license before then — otherwise the site falls back to the limited free edition (%{services} services). We'll remind you every 7 days.",
        { days: `${trialLengthDays}`, services: `${freeServicesLimit}` }
      )
    }}
  </TrialModeSelectionTrialStatus>
</template>
