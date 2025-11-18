<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Regex } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { X } from 'lucide-vue-next'
import { computed, nextTick, ref } from 'vue'

import usei18n from '@/lib/i18n'
import useClickOutside from '@/lib/useClickOutside'

import type { ValidationMessages } from '@/form/private/validation'

import FormSuggestions from './FormSuggestions.vue'
import FormToggleButton from './FormToggleButton.vue'

const { _t } = usei18n()

const { spec } = defineProps<{
  spec: Regex
  backendValidation: ValidationMessages
}>()

const data = defineModel<string>('data', { required: true, default: '' })
const inputType = ref('regex')

const vClickOutside = useClickOutside()

const placeholder = computed(() => {
  if (inputType.value === 'regex') {
    return _t('~Enter regex (pattern match)')
  } else if (inputType.value === 'text') {
    return _t('Enter plain text (single match)')
  }
  return ''
})

const suggestionsShown = ref(false)
const suggestionsRef = ref<InstanceType<typeof FormSuggestions> | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
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
  inputRef.value?.focus()
}
function hideSuggestions(): void {
  suggestionsShown.value = false
  inputRef.value?.focus()
}

const maxLabelLength = 60

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
      v-click-outside="
        () => {
          if (suggestionsShown) suggestionsShown = false
        }
      "
    >
      <div class="form-regex__input-button-wrap">
        <input
          ref="inputRef"
          v-model="data"
          class="form-regex__input"
          :aria-label="spec.label"
          :aria-expanded="suggestionsShown"
          :title="data.length > maxLabelLength ? data : ''"
          :placeholder="placeholder"
          maxlength="20"
          @click="showSuggestions"
          @keydown.down.prevent="onKeyDown"
          @keydown.up.prevent="onKeyUp"
          @keydown.enter.prevent="onKeyEnter"
        />
        <button v-if="data" type="button" class="form-regex__clear-btn" @click="data = ''">
          <X style="width: 1em; height: 1em" />
        </button>
      </div>
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

.form-regex__input-button-wrap {
  position: relative;
  width: 196px;
  display: inline-block;
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

.form-regex__input {
  border: 1px solid var(--color-mid-grey-60);
  padding: 0 2em 0 3px;
  height: 20px;
  border-left: 0;
  border-radius: 0 2px 2px 0;
  font-size: var(--font-size-normal);
  background-color: var(--ux-theme-5);
  position: relative;
  color: var(--font-color);
}

.form-regex__input:focus {
  border-color: var(--color-mid-grey-60);
  background-color: var(--ux-theme-5);
}

.form-regex__clear-btn {
  position: absolute;
  right: 1.2em;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  padding: 0;
  margin: 0;
  cursor: pointer;
  height: 1.5em;
  width: 1.5em;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
