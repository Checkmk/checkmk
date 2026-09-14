<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type TrialModeSelectionProps } from 'cmk-shared-typing/typescript/trial_mode_selection_props'
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import TrialModeSelectionEmailEntry from './screens/TrialModeSelectionEmailEntry.vue'
import TrialModeSelectionEntryChoice from './screens/TrialModeSelectionEntryChoice.vue'
import TrialModeSelectionLicenseVerification from './screens/TrialModeSelectionLicenseVerification.vue'
import { useTrialModeSelection } from './useTrialModeSelection'

const { _t } = usei18n()

const props = defineProps<TrialModeSelectionProps>()

const { screen, saving, saveFailed, goTo, verifyNow, verifyLater } = useTrialModeSelection(props)
</script>

<template>
  <div class="trial-mode-selection-app">
    <CmkAlertBox v-if="saveFailed" variant="error">
      {{ _t('Saving your selection failed. Please try again.') }}
    </CmkAlertBox>

    <TrialModeSelectionEntryChoice
      v-if="screen === 'choice'"
      :trial-length-days="props.trial_length_days"
      @trial="goTo('email')"
      @customer="goTo('verification')"
    />

    <TrialModeSelectionLicenseVerification
      v-else-if="screen === 'verification'"
      :saving="saving"
      @back="goTo('choice')"
      @verify-now="verifyNow"
      @verify-later="verifyLater"
    />

    <!-- No listener on @send-code yet: the code step arrives with the next change, and
         navigating to a screen that has no component would strand the dialog. -->
    <TrialModeSelectionEmailEntry
      v-else-if="screen === 'email'"
      :trial-length-days="props.trial_length_days"
      @back="goTo('choice')"
    />

    <CmkParagraph class="trial-mode-selection-app__footer">
      {{ _t('Signed in as %{user}.', { user: props.user_name }) }}
      <a :href="props.logout_url">{{ _t('Log out') }}</a>
    </CmkParagraph>
  </div>
</template>

<style scoped>
.trial-mode-selection-app__footer {
  color: var(--font-color-dimmed);
  margin-top: var(--dimension-8);

  a {
    color: var(--font-color-dimmed);
    text-decoration: underline;
  }
}
</style>
