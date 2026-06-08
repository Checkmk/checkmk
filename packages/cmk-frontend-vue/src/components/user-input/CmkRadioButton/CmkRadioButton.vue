<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { RadioGroupIndicator, RadioGroupItem } from 'reka-ui'

import type { TranslatedString } from '@/lib/i18nString'
import useId from '@/lib/useId'

import CmkHtml from '@/components/CmkHtml.vue'
import CmkLabel from '@/components/CmkLabel.vue'

interface CmkRadioButtonProps {
  value: string
  label?: TranslatedString
  help?: TranslatedString
  disabled?: boolean
}

const { value, label, help, disabled = false } = defineProps<CmkRadioButtonProps>()

const id = useId()
</script>

<template>
  <div class="cmk-radio-button">
    <RadioGroupItem :id="id" :value="value" class="cmk-radio-button__button" :disabled="disabled">
      <RadioGroupIndicator class="cmk-radio-button__indicator" />
    </RadioGroupItem>
    <template v-if="label">
      <CmkLabel :for="id" :help="help" cursor="inherit">
        <CmkHtml class="cmk-radio-button__label" :html="label" />
      </CmkLabel>
    </template>
  </div>
</template>

<style scoped>
.cmk-radio-button {
  display: flex;
  align-items: center;
  height: var(--dimension-6);
  cursor: pointer;

  &:has([data-disabled]) {
    cursor: not-allowed;
    opacity: 0.6;
  }
}

.cmk-radio-button__button {
  --radio-button-border-color: var(--color-mid-grey-50);

  box-sizing: border-box;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-shrink: 0;
  width: var(--dimension-6);
  height: var(--dimension-6);
  padding: 0;
  margin: 0;
  background-color: var(--default-form-element-bg-color);
  border: 1px solid var(--radio-button-border-color);
  border-radius: 50%;
  box-shadow: none; /* disable active/focus style of button */

  &:hover {
    background-color: var(--input-hover-bg-color);
  }

  &[data-disabled] {
    /* disabled <button> ignores `cursor`; let pointer events fall through so the
     parent's `not-allowed` cursor applies over the indicator too */
    pointer-events: none;
  }
}

body[data-theme='modern-dark'] .cmk-radio-button__button {
  --radio-button-border-color: var(--color-mid-grey-60);
}

.cmk-radio-button__indicator {
  width: var(--dimension-4);
  height: var(--dimension-4);
  border-radius: 50%;
  background-color: var(--font-color);
}

.cmk-radio-button__label {
  /* spacing lives inside the label so the gap to the button is clickable */
  padding-left: var(--spacing-half);
}
</style>
