<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

const { step, total, label } = defineProps<{
  /** 1-based position of the current step. */
  step: number
  total: number
  /** Names the step, e.g. "Email". */
  label: TranslatedString
}>()

const { _t } = usei18n()
</script>

<template>
  <div class="trial-mode-selection-step-indicator">
    <!-- The dots repeat what the text says, so they are decoration as far as a screen
         reader is concerned. -->
    <span
      v-for="dot in total"
      :key="dot"
      aria-hidden="true"
      class="trial-mode-selection-step-indicator__dot"
      :class="{
        'trial-mode-selection-step-indicator__dot--done': dot < step,
        'trial-mode-selection-step-indicator__dot--current': dot === step
      }"
    />
    <span class="trial-mode-selection-step-indicator__label">
      {{ _t('Step %{step} of %{total}', { step: `${step}`, total: `${total}` }) }} ·
      {{ label }}
    </span>
  </div>
</template>

<style scoped>
.trial-mode-selection-step-indicator {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}

.trial-mode-selection-step-indicator__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--default-form-element-border-color);
}

.trial-mode-selection-step-indicator__dot--current {
  background: var(--success);
}

/* Steps already behind us stay green, dimmed, so the row reads as progress rather
   than as a set of equal markers. */
.trial-mode-selection-step-indicator__dot--done {
  background: var(--success);
  opacity: 0.5;
}

.trial-mode-selection-step-indicator__label {
  margin-left: var(--dimension-2);
  color: var(--font-color-dimmed);
  font-size: var(--font-size-small);
}
</style>
