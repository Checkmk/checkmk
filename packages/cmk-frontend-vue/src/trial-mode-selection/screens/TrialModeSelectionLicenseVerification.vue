<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VerificationMode } from 'cmk-shared-typing/typescript/trial_mode_selection_request'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkLinkCard from 'cmk-ui-library/components/CmkLinkCard'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import TrialModeSelectionDialogFooter from '../components/TrialModeSelectionDialogFooter.vue'
import TrialModeSelectionScreenHeading from '../components/TrialModeSelectionScreenHeading.vue'

const { saving } = defineProps<{
  saving: boolean
}>()

const emit = defineEmits<{
  back: []
  /** Records the customer choice and opens the chosen verification page. */
  verifyNow: [mode: VerificationMode]
  /** Records the customer choice and leaves for the dashboard. */
  verifyLater: []
}>()

const { _t } = usei18n()
</script>

<template>
  <div class="trial-mode-selection-license-verification">
    <TrialModeSelectionScreenHeading>
      {{ _t('Verify your license') }}
    </TrialModeSelectionScreenHeading>
    <CmkParagraph class="trial-mode-selection-license-verification__subtitle">
      {{ _t('Choose how to validate the license for this site.') }}
    </CmkParagraph>

    <div class="trial-mode-selection-license-verification__options">
      <!--
        We use in-page navigation using CmkLinkCard with a `callback` parameter.
        It is the responsibility of the callback function to make sure there are no in-flight requests
        by checking the `saving` property.
        Note that using the `url` parameter would trigger a browser navigation which would cancel the in-flight requests.
        Note that merely setting the `disabled` property is insufficient:
        the CmkLinkCard element can still be activated using keyboard navigation.
       -->
      <CmkLinkCard
        icon-name="globe"
        :title="_t('Verify online')"
        :subtitle="_t('Validate automatically against the Checkmk license server.')"
        :open-in-new-tab="false"
        :disabled="saving"
        :callback="() => emit('verifyNow', 'online')"
      />
      <CmkLinkCard
        icon-name="upload"
        :title="_t('Verify offline')"
        :subtitle="_t('Upload a verification file exported from the customer portal.')"
        :open-in-new-tab="false"
        :disabled="saving"
        :callback="() => emit('verifyNow', 'offline')"
      />
    </div>

    <TrialModeSelectionDialogFooter :back-disabled="saving" @back="emit('back')">
      <CmkButton variant="optional" :running="saving" @click="emit('verifyLater')">
        {{ _t('Verify later') }}
      </CmkButton>
    </TrialModeSelectionDialogFooter>
  </div>
</template>

<style scoped>
.trial-mode-selection-license-verification__subtitle {
  color: var(--font-color-dimmed);
  margin-bottom: var(--dimension-8);
}

.trial-mode-selection-license-verification__options {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
  margin-top: var(--dimension-6);
}
</style>
