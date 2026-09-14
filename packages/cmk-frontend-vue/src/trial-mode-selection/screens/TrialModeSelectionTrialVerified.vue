<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { fromDate, toCalendarDate } from '@internationalized/date'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import { useResolvedDateTimeSettings } from 'cmk-ui-library/components/date-time'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import TrialModeSelectionDialogFooter from '../components/TrialModeSelectionDialogFooter.vue'
import TrialModeSelectionScreenHeading from '../components/TrialModeSelectionScreenHeading.vue'
import TrialModeSelectionStepIndicator from '../components/TrialModeSelectionStepIndicator.vue'

const { email, editionTitle, trialEndTimestamp, trialLengthDays, saving } = defineProps<{
  email: string
  editionTitle: string
  /** When the trial runs out, as a Unix timestamp. */
  trialEndTimestamp: number
  trialLengthDays: number
  saving: boolean
}>()

const emit = defineEmits<{
  startMonitoring: []
}>()

const { _t } = usei18n()

const dateTimeSettings = useResolvedDateTimeSettings()

// The day the admin reading this will see it end, so it is their own calendar
// day rather than the site's.
const endDate = computed(() =>
  dateTimeSettings.formatLongDate(
    toCalendarDate(fromDate(new Date(trialEndTimestamp * 1000), dateTimeSettings.timeZone))
  )
)

const summary = computed(() =>
  _t(
    'This site is now linked to %{email}. Your %{days}-day trial of %{edition} runs until %{endDate} — after that, the site reverts to the free edition unless you add a license.',
    { email, days: `${trialLengthDays}`, edition: editionTitle, endDate: endDate.value }
  )
)
</script>

<template>
  <div class="trial-mode-selection-trial-verified">
    <TrialModeSelectionStepIndicator :step="3" :total="3" :label="_t('Done')" />
    <div class="trial-mode-selection-trial-verified__check">
      <CmkIcon name="checkmark" size="large" />
    </div>
    <TrialModeSelectionScreenHeading>
      {{ _t('Trial verified') }}
    </TrialModeSelectionScreenHeading>
    <CmkParagraph class="trial-mode-selection-trial-verified__summary">
      {{ summary }}
    </CmkParagraph>

    <!-- Nowhere left to go back to: the branch is done, and this is where it is
         recorded. -->
    <TrialModeSelectionDialogFooter :show-back="false">
      <CmkButton variant="success" :running="saving" @click="emit('startMonitoring')">
        {{ _t('Start monitoring') }}
      </CmkButton>
    </TrialModeSelectionDialogFooter>
  </div>
</template>

<style scoped>
.trial-mode-selection-trial-verified__check {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  margin: var(--dimension-6) 0 var(--dimension-5);
  border-radius: 50%;
  background: var(--color-corporate-green-30);
}

.trial-mode-selection-trial-verified__summary {
  color: var(--font-color-dimmed);
  margin-top: var(--dimension-5);
}
</style>
