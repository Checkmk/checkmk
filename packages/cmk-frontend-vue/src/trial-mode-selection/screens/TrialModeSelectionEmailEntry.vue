<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkLink from 'cmk-ui-library/components/CmkLink.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import useId from 'cmk-ui-library/lib/useId'
import { computed, ref } from 'vue'

import TrialModeSelectionDialogFooter from '../components/TrialModeSelectionDialogFooter.vue'
import TrialModeSelectionScreenHeading from '../components/TrialModeSelectionScreenHeading.vue'
import TrialModeSelectionStepIndicator from '../components/TrialModeSelectionStepIndicator.vue'
import { LEGAL_LINKS } from '../legalLinks'

const email = ref('')
// NOTE: placeholder that will be replaced with CMK-39398, nothing subscribes yet.
const newsletterOptIn = ref(false)

const { trialLengthDays } = defineProps<{
  trialLengthDays: number
}>()

const emit = defineEmits<{
  back: []
  /** The address is well-formed; the code step takes it from here. */
  sendCode: []
}>()

const { _t } = usei18n()
const emailFieldId = useId()

/**
 * Owned here rather than handed to CmkInput's `validators`, which run on every
 * keystroke - nobody wants to be told their address is invalid while they are still
 * typing it. CmkInput reports nothing about its own validity, so the predicate has to
 * live on this side anyway.
 */
const emailErrors = ref<string[]>([])

const isWellFormed = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()))

/**
 * The sentence carrying the unsubscribe link stays one msgid with a placeholder, as the
 * acknowledge dialog writes it: split into fragments, the word order around the link
 * would not survive translation.
 */
const newsletterLabelParts = computed(() =>
  _t(
    'I agree to receive email newsletters about Checkmk products and services. I can unsubscribe via %{link}.'
  ).split('%{link}')
)

interface LegalNoticeLink {
  href: string
  label: TranslatedString
  /** Set where the visible text alone does not tell this link apart from another. */
  ariaLabel?: TranslatedString
}

type LegalNoticeSegment = LegalNoticeLink | { text: string }

/**
 * The consent notice stays one msgid for the same reason, with more riding on it: it
 * carries four links, and a translator has to be free to reorder the sentence around all
 * of them. The placeholder is kept in the split, so each link lands where the translation
 * puts it rather than where English did; one that no longer matches falls through as
 * literal text instead of a hole in the sentence.
 */
const legalNoticeLinks = computed(
  (): Record<string, LegalNoticeLink> => ({
    '%{terms}': { href: LEGAL_LINKS.terms, label: _t('General Terms & Conditions') },
    '%{eula}': { href: LEGAL_LINKS.eula, label: _t('EULA') },
    // "email" also names the link in the opt-in above, and a screen reader lists the two
    // side by side with nothing to tell them apart. The visible word stays, so the
    // sentence still reads as written.
    '%{unsubscribe}': {
      href: LEGAL_LINKS.unsubscribe,
      label: _t('email'),
      ariaLabel: _t('unsubscribe from onboarding emails by email')
    },
    '%{privacy_policy}': { href: LEGAL_LINKS.privacy, label: _t('Privacy Policy') }
  })
)

const legalNoticeSegments = computed((): LegalNoticeSegment[] =>
  _t(
    'I agree to the %{terms} and the %{eula}. I will receive Checkmk trial onboarding emails and can unsubscribe any time via %{unsubscribe}. I have noted the %{privacy_policy}.'
  )
    .split(/(%\{\w+\})/)
    .map((part) => legalNoticeLinks.value[part] ?? { text: part })
)

/**
 * The link sits inside the checkbox's own `<label>`, where a plain click would activate
 * the control as its default action and silently flip the opt-in. Cancelling the event
 * is the only thing that stops that, so the navigation has to be made explicitly.
 */
function openUnsubscribeInfo(event: MouseEvent): void {
  event.preventDefault()
  window.open(LEGAL_LINKS.unsubscribe, '_blank', 'noopener')
}

function submit(): void {
  if (!isWellFormed.value) {
    emailErrors.value = [_t('Enter a valid email address.')]
    return
  }
  emailErrors.value = []
  email.value = email.value.trim()
  emit('sendCode')
}

function clearErrors(): void {
  if (emailErrors.value.length > 0) {
    emailErrors.value = []
  }
}
</script>

<template>
  <div class="trial-mode-selection-email-entry">
    <TrialModeSelectionStepIndicator :step="1" :total="3" :label="_t('Email')" />
    <TrialModeSelectionScreenHeading>
      {{ _t('Verify your email address') }}
    </TrialModeSelectionScreenHeading>
    <CmkParagraph class="trial-mode-selection-email-entry__subtitle">
      {{
        _t("We'll email you a one-time code to activate your verified %{days}-day trial.", {
          days: `${trialLengthDays}`
        })
      }}
    </CmkParagraph>

    <CmkLabel :for="emailFieldId">{{ _t('Email address') }}</CmkLabel>
    <CmkInput
      :id="emailFieldId"
      v-model="email"
      type="text"
      field-size="fill"
      placeholder="you@company.com"
      :external-errors="emailErrors"
      @input="clearErrors"
      @keydown.enter.prevent="submit"
    />

    <CmkParagraph class="trial-mode-selection-email-entry__hint">
      {{
        _t(
          'Use an address you can access now — codes expire after 24 hours. Verification links this site to your trial registration.'
        )
      }}
    </CmkParagraph>

    <CmkCheckbox v-model="newsletterOptIn" class="trial-mode-selection-email-entry__newsletter">
      <template #label>
        {{ newsletterLabelParts[0]
        }}<CmkLink
          class="trial-mode-selection-email-entry__inline-link"
          :href="LEGAL_LINKS.unsubscribe"
          :aria-label="_t('unsubscribe from the newsletter by email')"
          target="_blank"
          rel="noopener"
          @click="openUnsubscribeInfo"
          >{{ _t('email') }}</CmkLink
        >{{ newsletterLabelParts[1] }}
      </template>
    </CmkCheckbox>

    <!-- Not a second checkbox: pressing "Send code" is the agreement. -->
    <CmkParagraph class="trial-mode-selection-email-entry__legal">
      <template v-for="(segment, index) in legalNoticeSegments" :key="index"
        ><CmkLink
          v-if="'href' in segment"
          class="trial-mode-selection-email-entry__inline-link"
          :href="segment.href"
          :aria-label="segment.ariaLabel"
          target="_blank"
          rel="noopener"
          >{{ segment.label }}</CmkLink
        ><template v-else>{{ segment.text }}</template></template
      >
    </CmkParagraph>

    <TrialModeSelectionDialogFooter @back="emit('back')">
      <CmkButton variant="success" @click="submit">{{ _t('Send code') }}</CmkButton>
    </TrialModeSelectionDialogFooter>
  </div>
</template>

<style scoped>
.trial-mode-selection-email-entry__subtitle {
  color: var(--font-color-dimmed);
  margin-bottom: var(--dimension-8);
}

.trial-mode-selection-email-entry__hint {
  color: var(--font-color-dimmed);
  font-size: var(--font-size-small);
  margin-top: var(--dimension-5);
}

.trial-mode-selection-email-entry__newsletter {
  margin-top: var(--dimension-6);
}

.trial-mode-selection-email-entry__legal {
  color: var(--font-color-dimmed);
  font-size: var(--font-size-small);
  margin-top: var(--dimension-6);
  padding-top: var(--dimension-5);
  border-top: 1px solid var(--ux-theme-6);
}

/* `.cmk-link` is `display: flex; width: 100%`, which would break these out of the
   sentences they belong to. */
.trial-mode-selection-email-entry__inline-link {
  display: inline;
  width: auto;
  font-size: inherit;
}
</style>
