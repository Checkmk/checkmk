<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type TrialModeSelection } from 'cmk-shared-typing/typescript/trial_mode_selection'
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkLinkCard from 'cmk-ui-library/components/CmkLinkCard'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import { cmkAjax } from 'cmk-ui-library/lib/ajax'
import usei18n from 'cmk-ui-library/lib/i18n'
import { type ComponentPublicInstance, nextTick, ref } from 'vue'

import { getCsrfToken } from '@/lib/csrf'

const { _t } = usei18n()

const props = defineProps<TrialModeSelection>()

/**
 * State of the trial mode selection flow.
 *
 * 'mode' is the initial step when the user needs to select between "trial" and "customer".
 * 'verification' is the step in which a user that has previously selected "customer" falls into.
 * In the 'verification' step the user is asked to choose if they want to verify the license in an "online" or "offline" way
 * @default 'mode'
 */
const step = ref<'mode' | 'verification'>('mode')
const saving = ref(false)
const error = ref(false)
const stepHeading = ref<ComponentPublicInstance | null>(null)

/*
 * Persists the decision and only then leaves the page.
 */
async function decide(selection: 'trial' | 'customer', target: string): Promise<void> {
  if (saving.value) {
    return
  }
  saving.value = true
  error.value = false
  try {
    await cmkAjax(props.save_url, {
      selection,
      _csrf_token: getCsrfToken()
    })
    window.location.assign(target)
  } catch (e) {
    saving.value = false
    error.value = true
    console.error(e)
  }
}

async function goToStep(next: 'mode' | 'verification'): Promise<void> {
  // Switching steps is blocked while a save is in flight, because that save
  // navigates away on its own once it succeeds.
  if (saving.value) {
    return
  }
  error.value = false
  step.value = next
  // Activating a card unmounts it, and the browser then resets focus to the
  // document body: a keyboard user loses their place and a screen reader
  // announces nothing. Move focus to the heading instead, after nextTick so
  // it already shows the new step's title.
  await nextTick()
  const element = stepHeading.value?.$el
  if (element instanceof HTMLElement) {
    element.focus()
  }
}
</script>

<template>
  <div class="trial-mode-selection-app">
    <template v-if="step === 'mode'">
      <CmkHeading ref="stepHeading" type="h1" tabindex="-1">
        {{ _t('Welcome to your new Checkmk site') }}
      </CmkHeading>
      <CmkParagraph class="trial-mode-selection-app__subtitle">
        {{ _t("Tell us how you're using this site so we can set it up correctly.") }}
      </CmkParagraph>
    </template>
    <template v-else>
      <CmkHeading ref="stepHeading" type="h1" tabindex="-1">
        {{ _t('Verify your license') }}
      </CmkHeading>
      <CmkParagraph class="trial-mode-selection-app__subtitle">
        {{ _t('Choose how to validate the license for this site.') }}
      </CmkParagraph>
    </template>
    <CmkAlertBox v-if="error" variant="error">
      {{ _t('Saving your selection failed. Please try again.') }}
    </CmkAlertBox>

    <div class="trial-mode-selection-app__options">
      <template v-if="step === 'mode'">
        <!--
          We use in-page navigation using CmkLinkCard with a `callback` parameter.
          It is the responsibility of the callback function to make sure there are no in-flight requests
          by checking the `saving` property.
          Note that using the `url` parameter would trigger a browser navigation which would cancel the in-flight requests.
          Note that merely setting the `disabled` property is insufficient:
          the CmkLinkCard element can still be activated using keyboard navigation.
         -->
        <CmkLinkCard
          icon-name="start"
          :title="_t('Start a trial')"
          :subtitle="_t('Try all features of Checkmk free for 30 days.')"
          :open-in-new-tab="false"
          :disabled="saving"
          :callback="() => decide('trial', 'index.py')"
        />
        <CmkLinkCard
          icon-name="signature-key"
          :title="_t('I\'m an existing customer')"
          :subtitle="_t('Verify your license to activate this site.')"
          :open-in-new-tab="false"
          :disabled="saving"
          :callback="() => goToStep('verification')"
        />
      </template>
      <template v-else>
        <CmkLinkCard
          icon-name="globe"
          :title="_t('Verify online')"
          :subtitle="_t('Validate automatically against the Checkmk license server.')"
          :open-in-new-tab="false"
          :disabled="saving"
          :callback="() => decide('customer', props.verify_online_url)"
        />
        <CmkLinkCard
          icon-name="upload"
          :title="_t('Verify offline')"
          :subtitle="_t('Upload a verification file exported from the customer portal.')"
          :open-in-new-tab="false"
          :disabled="saving"
          :callback="() => decide('customer', props.verify_offline_url)"
        />
      </template>
    </div>

    <div v-if="step === 'verification'" class="trial-mode-selection-app__actions">
      <CmkButton
        variant="optional"
        :icon="{ name: 'back', side: 'left' }"
        :running="saving"
        @click="goToStep('mode')"
      >
        {{ _t('Back') }}
      </CmkButton>
      <CmkButton variant="optional" :running="saving" @click="decide('customer', 'index.py')">
        {{ _t('Verify later') }}
      </CmkButton>
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

.trial-mode-selection-app__actions {
  display: flex;
  justify-content: space-between;
  gap: var(--dimension-6);
  margin-top: var(--dimension-8);
  padding-top: var(--dimension-6);
  border-top: var(--dimension-1) solid var(--ux-theme-6);
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
