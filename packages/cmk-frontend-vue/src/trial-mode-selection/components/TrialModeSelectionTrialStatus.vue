<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkBadge from 'cmk-ui-library/components/CmkBadge.vue'
import type { Colors } from 'cmk-ui-library/components/CmkBadge.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import TrialModeSelectionDialogFooter from './TrialModeSelectionDialogFooter.vue'
import TrialModeSelectionScreenHeading from './TrialModeSelectionScreenHeading.vue'

const { badgeLabel, badgeColor, trialEndTimestamp, trialLengthDays, saving } = defineProps<{
  badgeLabel: TranslatedString
  badgeColor: Colors
  /** When the trial runs out, as a timestamp. */
  trialEndTimestamp: number
  trialLengthDays: number
  saving: boolean
}>()

const emit = defineEmits<{
  back: []
  startMonitoring: []
}>()

const { _t, _tn } = usei18n()

// Capped at the trial length, in case the browser clock is behind the site's.
const daysLeft = computed(() =>
  Math.min(trialLengthDays, Math.ceil((trialEndTimestamp - Date.now() / 1000) / 86400))
)
</script>

<template>
  <div class="trial-mode-selection-trial-status">
    <div class="trial-mode-selection-trial-status__title">
      <TrialModeSelectionScreenHeading>
        <CmkBadge :color="badgeColor" type="outline">{{ badgeLabel }}</CmkBadge>
      </TrialModeSelectionScreenHeading>
      <!-- Hidden once the trial has ended: the free edition banner takes over then. -->
      <CmkParagraph v-if="daysLeft > 0" class="trial-mode-selection-trial-status__dimmed">
        {{
          _tn('Full features · %{days} day left', 'Full features · %{days} days left', daysLeft, {
            days: `${daysLeft}`
          })
        }}
      </CmkParagraph>
    </div>

    <CmkParagraph class="trial-mode-selection-trial-status__dimmed">
      <slot />
    </CmkParagraph>

    <TrialModeSelectionDialogFooter :back-disabled="saving" @back="emit('back')">
      <CmkButton variant="success" :running="saving" @click="emit('startMonitoring')">
        {{ _t('Start monitoring') }}
      </CmkButton>
    </TrialModeSelectionDialogFooter>
  </div>
</template>

<style scoped>
.trial-mode-selection-trial-status__title {
  display: flex;
  align-items: center;
  gap: var(--dimension-5);
  margin-bottom: var(--dimension-6);
}

.trial-mode-selection-trial-status__dimmed {
  color: var(--font-color-dimmed);
}
</style>
