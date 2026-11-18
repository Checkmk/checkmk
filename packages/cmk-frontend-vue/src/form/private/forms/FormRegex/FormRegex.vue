<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Regex } from 'cmk-shared-typing/typescript/vue_formspec_components'
import usei18n from 'cmk-ui-library/lib/i18n'
import { useWidgetKeys } from 'cmk-ui-library/lib/keyboardHelp'
import useClickOutside from 'cmk-ui-library/lib/useClickOutside'
import { nextTick, ref } from 'vue'

import type { ValidationMessages } from '@/form/private/validation'

import FormSuggestions from './FormSuggestions.vue'
import FormToggleButton from './FormToggleButton.vue'
import RegexInput, { type RegexMode } from './RegexInput.vue'

const { _t } = usei18n()
useWidgetKeys(_t('Regex input'), [
  { combo: ['ArrowDown'], description: _t('Move through suggestions') },
  { combo: ['ArrowUp'], description: _t('Move through suggestions') },
  { combo: ['Enter'], description: _t('Pick suggestion') }
])

const { spec } = defineProps<{
  spec: Regex
  backendValidation: ValidationMessages
}>()

const data = defineModel<string>('data', { required: true, default: '' })
const inputType = ref<RegexMode>('regex')

const vClickOutside = useClickOutside()

const suggestionsShown = ref(false)
const suggestionsRef = ref<InstanceType<typeof FormSuggestions> | null>(null)
const regexInput = ref<InstanceType<typeof RegexInput> | null>(null)
const isFocused = ref(false)

function showSuggestions(): void {
  isFocused.value = !isFocused.value
  suggestionsShown.value = !suggestionsShown.value
  if (!suggestionsShown.value) {
    return
  }
  // eslint-disable-next-line @typescript-eslint/no-floating-promises
  nextTick(async () => {
    if (suggestionsRef.value?.rootRef) {
      const el = suggestionsRef.value.rootRef as HTMLElement
      const suggestionsRect = el.getBoundingClientRect()
      if (window.innerHeight - suggestionsRect.bottom < suggestionsRect.height) {
        el.style.bottom = `calc(2 * var(--spacing))`
      } else {
        el.style.removeProperty('bottom')
      }
      await focus()
    }
  })
}

async function focus(): Promise<void> {
  regexInput.value?.focus()
}
function hideSuggestions(): void {
  suggestionsShown.value = false
  regexInput.value?.focus()
}

function onKeyDown(e: KeyboardEvent) {
  e.stopPropagation()
  if (suggestionsRef.value) {
    suggestionsRef.value.selectNextElement()
  }
}
function onKeyUp(e: KeyboardEvent) {
  e.stopPropagation()
  if (suggestionsRef.value) {
    suggestionsRef.value.selectPreviousElement()
  }
}
function onKeyEnter(e: KeyboardEvent) {
  e.stopPropagation()
  if (suggestionsRef.value) {
    suggestionsRef.value.selectHighlightedSuggestion()
    hideSuggestions()
  }
}
</script>
<template>
  <div class="form-regex__text-input">
    <FormToggleButton v-model="inputType" />
    <div
      v-click-outside="{
        open: suggestionsShown,
        close: () => {
          if (suggestionsShown) suggestionsShown = false
        }
      }"
    >
      <RegexInput
        ref="regexInput"
        v-model="data"
        :mode="inputType"
        :label="spec.label"
        :maxlength="20"
        :aria-expanded="suggestionsShown"
        @click="showSuggestions"
        @keydown.down.prevent="onKeyDown"
        @keydown.up.prevent="onKeyUp"
        @keydown.enter.prevent="onKeyEnter"
      />
      <FormSuggestions
        v-if="suggestionsShown"
        ref="suggestionsRef"
        v-model:data="data"
        :type="inputType"
        :spec="spec"
        @request-close-suggestions="hideSuggestions"
      />
      <div v-if="suggestionsShown" class="form-regex__bottom-fill"></div>
    </div>
  </div>
</template>

<style scoped>
.form-regex__text-input {
  display: flex;
  align-items: center;
  position: relative;
}

.form-regex__bottom-fill {
  position: absolute;
  left: 0;
  bottom: 0;
  height: 10px;
  background: var(--ux-theme-5);
  transform: translate(1px, 2px);
  width: 85px;
}
</style>
