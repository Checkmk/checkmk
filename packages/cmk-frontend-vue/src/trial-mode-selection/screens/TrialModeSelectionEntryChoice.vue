<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLinkCard from 'cmk-ui-library/components/CmkLinkCard'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import TrialModeSelectionScreenHeading from '../components/TrialModeSelectionScreenHeading.vue'

const { trialLengthDays } = defineProps<{
  trialLengthDays: number
}>()

const emit = defineEmits<{
  /** Opens the trial branch. */
  trial: []
  /** Opens the branch asking an existing customer how to verify the license. */
  customer: []
}>()

const { _t } = usei18n()
</script>

<template>
  <div class="trial-mode-selection-entry-choice">
    <TrialModeSelectionScreenHeading>
      {{ _t('Welcome to your new Checkmk site') }}
    </TrialModeSelectionScreenHeading>
    <CmkParagraph class="trial-mode-selection-entry-choice__subtitle">
      {{ _t("Tell us how you're using this site so we can set it up correctly.") }}
    </CmkParagraph>
    <div class="trial-mode-selection-entry-choice__options">
      <!-- Both cards continue inside the dialog, so they navigate through a `callback`
           rather than a `url`, which would hand the page to the browser. Neither of
           them records anything: no save can be in flight on this screen. -->
      <CmkLinkCard
        icon-name="start"
        :title="_t('Start a trial')"
        :subtitle="
          _t('Try all features of Checkmk free for %{days} days.', {
            days: `${trialLengthDays}`
          })
        "
        :open-in-new-tab="false"
        :callback="() => emit('trial')"
      />
      <CmkLinkCard
        icon-name="signature-key"
        :title="_t('I\'m an existing customer')"
        :subtitle="_t('Verify your license to activate this site.')"
        :open-in-new-tab="false"
        :callback="() => emit('customer')"
      />
    </div>
  </div>
</template>

<style scoped>
.trial-mode-selection-entry-choice__subtitle {
  color: var(--font-color-dimmed);
  margin-bottom: var(--dimension-8);
}

.trial-mode-selection-entry-choice__options {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
  margin-top: var(--dimension-6);
}
</style>
