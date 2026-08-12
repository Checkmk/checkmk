<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type TrialModeSelection } from 'cmk-shared-typing/typescript/trial_mode_selection'
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkLinkCard from 'cmk-ui-library/components/CmkLinkCard'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import { cmkAjax } from 'cmk-ui-library/lib/ajax'
import usei18n from 'cmk-ui-library/lib/i18n'
import { ref } from 'vue'

// eslint-disable-next-line @typescript-eslint/naming-convention
declare let global_csrf_token: string

const { _t } = usei18n()

const props = defineProps<TrialModeSelection>()

const saving = ref(false)
const error = ref(false)

async function choose(selection: 'trial' | 'customer'): Promise<void> {
  if (saving.value) {
    return
  }
  saving.value = true
  error.value = false
  try {
    await cmkAjax(props.save_url, {
      selection,
      _csrf_token: global_csrf_token
    })
    window.location.assign('index.py')
  } catch (e) {
    saving.value = false
    error.value = true
    console.error(e)
  }
}
</script>

<template>
  <div class="trial-mode-selection-app">
    <CmkHeading type="h1">{{ _t('Welcome to your new Checkmk site') }}</CmkHeading>
    <CmkParagraph class="trial-mode-selection-app__subtitle">
      {{ _t("Tell us how you're using this site so we can set it up correctly.") }}
    </CmkParagraph>
    <CmkAlertBox v-if="error" variant="error">
      {{ _t('Saving your selection failed. Please try again.') }}
    </CmkAlertBox>
    <div class="trial-mode-selection-app__options">
      <CmkLinkCard
        icon-name="start"
        :title="_t('Start a trial')"
        :subtitle="_t('Try all features of Checkmk free for 30 days.')"
        :open-in-new-tab="false"
        :disabled="saving"
        :callback="() => choose('trial')"
      />
      <CmkLinkCard
        icon-name="signature-key"
        :title="_t('I\'m an existing customer')"
        :subtitle="_t('Verify your license to activate this site.')"
        :open-in-new-tab="false"
        :disabled="saving"
        :callback="() => choose('customer')"
      />
    </div>
    <CmkParagraph class="trial-mode-selection-app__footer">
      {{ _t('Signed in as %{user}.', { user: props.user_name }) }}
      <a :href="props.logout_url">{{ _t('Log out') }}</a>
    </CmkParagraph>
  </div>
</template>

<style scoped>
.trial-mode-selection-app__subtitle {
  color: var(--font-color-dimmed);
  margin-bottom: var(--dimension-8);
}

.trial-mode-selection-app__options {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
  margin-top: var(--dimension-6);
}

.trial-mode-selection-app__footer {
  color: var(--font-color-dimmed);
  margin-top: var(--dimension-8);

  a {
    color: var(--font-color-dimmed);
    text-decoration: underline;
  }
}
</style>
