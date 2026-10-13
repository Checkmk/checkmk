<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

import TrialModeSelectionTrialStatus from '../components/TrialModeSelectionTrialStatus.vue'
import { formatRepromptInterval } from '../repromptInterval'

const { trialEndTimestamp, trialLengthDays, freeServicesLimit, repromptHours } = defineProps<{
  /** When the trial runs out, as a timestamp. */
  trialEndTimestamp: number
  trialLengthDays: number
  /** Services the free edition monitors once the trial has ended. */
  freeServicesLimit: number
  /** Hours until the dialog reappears. */
  repromptHours: number
}>()

const emit = defineEmits<{
  startMonitoring: []
}>()

const { _t } = usei18n()
</script>

<template>
  <TrialModeSelectionTrialStatus
    :badge-label="_t('Unverified trial')"
    badge-color="warning"
    :trial-end-timestamp="trialEndTimestamp"
    :trial-length-days="trialLengthDays"
    @start-monitoring="emit('startMonitoring')"
  >
    {{
      _t(
        'Trial started without verification. Full features for %{days} days from site creation, then fallback to the limited free edition (%{services} services). While the site is under %{days} days old, the dialog reappears on admin login (at most once every %{interval}) as another chance to verify or license.',
        {
          days: `${trialLengthDays}`,
          services: `${freeServicesLimit}`,
          interval: formatRepromptInterval(repromptHours)
        }
      )
    }}
  </TrialModeSelectionTrialStatus>
</template>
