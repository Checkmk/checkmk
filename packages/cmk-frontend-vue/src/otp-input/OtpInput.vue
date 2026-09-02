<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { ref, watch } from 'vue'

/** Digits a one-time code is made of. Both the grouping gap and the model length follow it. */
const DIGIT_COUNT = 6
/** Index the wider gap sits after, splitting the code into two even halves. */
const GROUP_SPLIT_INDEX = DIGIT_COUNT / 2 - 1

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
const internalDigits = ref<string[]>(new Array(DIGIT_COUNT).fill(''))

watch(
  () => modelValue.value,
  (newVal) => {
    // Only an externally driven model reaches the boxes. Our own edits already wrote the boxes,
    // and the model they produced has any gap compacted out of it - redistributing that back
    // would shift the digits after a cleared box one place left.
    if (internalDigits.value.join('') === newVal) {
      return
    }
    const codes = newVal.split('').slice(0, DIGIT_COUNT)
    internalDigits.value = [...codes, ...new Array(DIGIT_COUNT - codes.length).fill('')]
  },
  // Immediate, so a code handed in as the initial model shows up in the boxes. The app-local
  // predecessor was only ever mounted with an empty model, so it could do without.
  { immediate: true }
)

defineExpose({
  focus: () => {
    otpInputs.value[0]?.focus()
  }
})

function handleInput(event: Event, index: number) {
  const input = event.target as HTMLInputElement
  // The field is a text input, so nothing but this keeps letters out of the boxes - the
  // `pattern` attribute constrains form validation, not typing.
  const val = input.value.replace(/\D/g, '').slice(0, 1)
  input.value = val
  internalDigits.value[index] = val
  modelValue.value = internalDigits.value.join('')

  if (val && index < DIGIT_COUNT - 1) {
    otpInputs.value[index + 1]?.focus()
  } else if (val && index === DIGIT_COUNT - 1) {
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
    }
  } else if (event.key === 'ArrowLeft' && index > 0) {
    otpInputs.value[index - 1]?.focus()
  } else if (event.key === 'ArrowRight' && index < DIGIT_COUNT - 1) {
    otpInputs.value[index + 1]?.focus()
  }
}

function handlePaste(event: ClipboardEvent) {
  event.preventDefault()
  const pasteData = event.clipboardData?.getData('text') || ''
  const numbers = pasteData.replace(/\D/g, '').split('').slice(0, DIGIT_COUNT)

  if (numbers.length > 0) {
    const paddedNumbers = [...numbers, ...new Array(DIGIT_COUNT - numbers.length).fill('')]
    internalDigits.value = paddedNumbers
    modelValue.value = internalDigits.value.join('')

    const focusIndex = Math.min(numbers.length, DIGIT_COUNT - 1)
    otpInputs.value[focusIndex]?.focus()

    if (numbers.length === DIGIT_COUNT) {
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
  <div class="otp-input">
    <input
      v-for="(_digit, index) in DIGIT_COUNT"
      ref="otpInputs"
      :key="index"
      :aria-label="
        _t('Digit %{count} of %{total}', { count: `${index + 1}`, total: `${DIGIT_COUNT}` })
      "
      type="text"
      inputmode="numeric"
      pattern="[0-9]*"
      maxlength="1"
      class="otp-input__digit"
      :class="[
        { 'otp-input__digit--split': index === GROUP_SPLIT_INDEX },
        { 'otp-input__digit--error': error }
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
/* No outer spacing: the surrounding layout owns that, so the component sits in a dialog
   as readily as on a page of its own. The gap is explicit rather than distributed with
   'space-between', which only produced an even rhythm at one particular container width. */
.otp-input {
  display: flex;
  gap: var(--dimension-3);
}

.otp-input__digit {
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

.otp-input__digit:focus {
  border-color: var(--success);
  background-color: var(--input-hover-bg-color);
}

.otp-input__digit--error {
  border-color: var(--inline-error-border-color);
}

.otp-input__digit--error:focus {
  border-color: var(--inline-error-border-color);
  background-color: var(--input-hover-bg-color);
}

.otp-input__digit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.otp-input__digit--split {
  margin-right: var(--spacing);
}
</style>
