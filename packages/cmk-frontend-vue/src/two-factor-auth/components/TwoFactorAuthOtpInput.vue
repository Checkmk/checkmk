<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

type Props = {
  disabled?: boolean
  error?: boolean
}

const { disabled = false, error = false } = defineProps<Props>()
const { _t } = usei18n()
const emit = defineEmits<{
  (e: 'submit'): void
}>()

const modelValue = defineModel<string>('modelValue', { default: '' })

const otpInputs = ref<HTMLInputElement[]>([])
const internalDigits = ref<string[]>(new Array(6).fill(''))

watch(
  () => modelValue.value,
  (newVal) => {
    const codes = newVal.split('').slice(0, 6)
    internalDigits.value = [...codes, ...new Array(6 - codes.length).fill('')]
  }
)

defineExpose({
  focus: () => {
    otpInputs.value[0]?.focus()
  }
})

function handleInput(event: Event, index: number) {
  const input = event.target as HTMLInputElement
  const val = input.value
  internalDigits.value[index] = val
  modelValue.value = internalDigits.value.join('')

  if (val && index < 5) {
    otpInputs.value[index + 1]?.focus()
  } else if (val && index === 5) {
    const allFilled = internalDigits.value.every((d) => d !== '' && d !== null)
    if (allFilled) {
      emit('submit')
    }
  }
}

function handleKeyEvents(event: KeyboardEvent, index: number) {
  if (event.key === 'Backspace') {
    if (!internalDigits.value[index] && index > 0) {
      internalDigits.value[index - 1] = ''
      modelValue.value = internalDigits.value.join('')
      otpInputs.value[index - 1]?.focus()
    } else if (internalDigits.value[index]) {
      internalDigits.value[index] = ''
      modelValue.value = internalDigits.value.join('')
    } else if (index > 0) {
      otpInputs.value[index - 1]?.focus()
    }
  } else if (event.key === 'ArrowLeft' && index > 0) {
    otpInputs.value[index - 1]?.focus()
  } else if (event.key === 'ArrowRight' && index < 5) {
    otpInputs.value[index + 1]?.focus()
  }
}

function handlePaste(event: ClipboardEvent) {
  event.preventDefault()
  const pasteData = event.clipboardData?.getData('text') || ''
  const numbers = pasteData.replace(/\D/g, '').split('').slice(0, 6)

  if (numbers.length > 0) {
    const paddedNumbers = [...numbers, ...new Array(6 - numbers.length).fill('')]
    internalDigits.value = paddedNumbers
    modelValue.value = internalDigits.value.join('')

    const focusIndex = Math.min(numbers.length, 5)
    otpInputs.value[focusIndex]?.focus()

    if (numbers.length === 6) {
      emit('submit')
    }
  }
}

function handleFocus(event: FocusEvent) {
  const input = event.target as HTMLInputElement
  input.select()
}
</script>

<template>
  <div class="two-factor-auth-otp-input">
    <input
      v-for="(_digit, index) in 6"
      ref="otpInputs"
      :key="index"
      :aria-label="_t('OTP Digit %{count}', { count: `${index + 1}` })"
      type="number"
      pattern="[0-9]*"
      maxlength="1"
      class="two-factor-auth-otp-input__digit"
      :class="[
        { 'two-factor-auth-otp-input__digit--split': index === 2 },
        { 'two-factor-auth-otp-input__digit--error': error }
      ]"
      :value="internalDigits[index]"
      :disabled="disabled"
      autocomplete="one-time-code"
      @input="handleInput($event, index)"
      @keydown="handleKeyEvents($event, index)"
      @paste="handlePaste"
      @focus="handleFocus($event)"
    />
  </div>
</template>

<style scoped>
.two-factor-auth-otp-input {
  display: flex;
  justify-content: space-between;
  padding-bottom: var(--dimension-8);
  padding-top: var(--dimension-5);
}

.two-factor-auth-otp-input__digit {
  width: 48px;
  height: 56px;
  font-size: var(--dimension-9);
  font-weight: var(--font-weight-bold);
  text-align: center;
  background-color: var(--ux-theme-5);
  border: var(--border-width-1) solid var(--default-form-element-border-color);
  border-radius: var(--dimension-3);
  color: var(--font-color);
  outline: none;
  padding: 0;
  transition: border-color 0.2s;
}

.two-factor-auth-otp-input__digit::-webkit-outer-spin-button,
.two-factor-auth-otp-input__digit::-webkit-inner-spin-button {
  appearance: none;
}

.two-factor-auth-otp-input__digit:focus {
  border-color: var(--success);
  background-color: var(--input-hover-bg-color);
}

.two-factor-auth-otp-input__digit--error {
  border-color: var(--inline-error-border-color);
}

.two-factor-auth-otp-input__digit--error:focus {
  border-color: var(--inline-error-border-color);
  background-color: var(--input-hover-bg-color);
}

.two-factor-auth-otp-input__digit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.two-factor-auth-otp-input__digit--split {
  margin-right: var(--spacing);
}
</style>
