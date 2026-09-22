<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed, nextTick, onMounted, ref } from 'vue'

import OtpInput from '@/otp-input/OtpInput.vue'
import { DIGIT_COUNT } from '@/otp-input/otpInput'

import TrialModeSelectionDialogFooter from '../components/TrialModeSelectionDialogFooter.vue'
import TrialModeSelectionScreenHeading from '../components/TrialModeSelectionScreenHeading.vue'
import TrialModeSelectionStepIndicator from '../components/TrialModeSelectionStepIndicator.vue'

const { email, resendCooldown } = defineProps<{
  email: string
  /** Seconds left before another code may be requested; 0 means it is available. */
  resendCooldown: number
}>()

const emit = defineEmits<{
  back: []
  resend: []
  verified: []
}>()

const { _t } = usei18n()

const codeInput = ref<InstanceType<typeof OtpInput> | null>(null)
const codeLabelId = useId()

/**
 * Local, not modelled upwards: nothing above this screen reads the code, and a model
 * threaded through the dialog would lag a tick behind the input's last digit - long
 * enough for the completion check below to still see five digits.
 */
const code = ref('')

const isComplete = computed(() => code.value.length === DIGIT_COUNT)
const canResend = computed(() => resendCooldown <= 0)

const resendLabel = computed(() =>
  canResend.value
    ? _t('Resend code')
    : _t('Resend code (%{countdown})', { countdown: formatCountdown(resendCooldown) })
)

function formatCountdown(seconds: number): string {
  const minutes = Math.floor(seconds / 60)
  return `${minutes}:${String(seconds % 60).padStart(2, '0')}`
}

/**
 * Nothing to check the code against yet - CMK-37828 takes it to the backend. Until then
 * any six digits complete the flow.
 */
function verify(): void {
  if (!isComplete.value) {
    return
  }
  emit('verified')
}

/**
 * Clear the boxes rather than leave digits behind that look ready to verify. Whether a
 * resend invalidates the code already sent is the backend's call, not something this
 * screen is in a position to promise.
 */
async function resend(): Promise<void> {
  code.value = ''
  emit('resend')
  await nextTick()
  codeInput.value?.focus()
}

onMounted(() => codeInput.value?.focus())
</script>

<template>
  <div class="trial-mode-selection-code-entry">
    <TrialModeSelectionStepIndicator :step="2" :total="3" :label="_t('Code')" />
    <TrialModeSelectionScreenHeading>
      {{ _t('Enter your verification code') }}
    </TrialModeSelectionScreenHeading>
    <CmkParagraph class="trial-mode-selection-code-entry__subtitle">
      {{
        _t('We sent a 6-digit code to %{email}. It expires after 24 hours.', {
          email
        })
      }}
    </CmkParagraph>

    <CmkLabel :id="codeLabelId">{{ _t('Verification code') }}</CmkLabel>
    <!-- The boxes submit on their own when the last one is the box being filled, and on a
         full paste. Enter is for a code completed out of order, a corrected digit say. -->
    <div
      class="trial-mode-selection-code-entry__code"
      role="group"
      :aria-labelledby="codeLabelId"
      @keydown.enter.prevent="verify"
    >
      <OtpInput ref="codeInput" v-model="code" @submit="verify" />
    </div>

    <div class="trial-mode-selection-code-entry__resend">
      <CmkParagraph class="trial-mode-selection-code-entry__resend-question">
        {{ _t("Didn't receive it?") }}
      </CmkParagraph>
      <CmkButton variant="optional" size="small" :disabled="!canResend" @click="resend">
        {{ resendLabel }}
      </CmkButton>
    </div>

    <TrialModeSelectionDialogFooter @back="emit('back')">
      <CmkButton variant="success" :disabled="!isComplete" @click="verify">
        {{ _t('Verify') }}
      </CmkButton>
    </TrialModeSelectionDialogFooter>
  </div>
</template>

<style scoped>
.trial-mode-selection-code-entry__subtitle {
  color: var(--font-color-dimmed);
  margin-bottom: var(--dimension-8);
}

.trial-mode-selection-code-entry__code {
  margin: var(--dimension-4) 0 var(--dimension-6);
}

.trial-mode-selection-code-entry__resend {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.trial-mode-selection-code-entry__resend-question {
  color: var(--font-color-dimmed);
  font-size: var(--font-size-small);
}
</style>
