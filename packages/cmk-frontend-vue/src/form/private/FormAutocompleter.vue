<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { setupAutocompleter } from '@/form/components/utils/autocompleter'
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { X } from 'lucide-vue-next'
import CmkSuggestions from '@/components/CmkSuggestions.vue'
import useClickOutside from '@/lib/useClickOutside'

const props = defineProps<{
  id?: string
  placeholder: string
  autocompleter?: Autocompleter | null
  filterOn: string[]
  size: number
  resestInputOnAdd: boolean
}>()

type Suggestion = [string, string]
const inputValue = defineModel<string>()
const visibleInputValue = ref<string>('')

const emit = defineEmits<{
  (e: 'select', value: string): void
}>()

type AutocompleterResponse = Record<'choices', Suggestion[]>
const { input: autocompleterInput, output: autocompleterOutput } =
  setupAutocompleter<AutocompleterResponse>(() => props.autocompleter || null)
const filteredSuggestions = ref<Suggestion[]>([])
const suggestionsRef = ref<InstanceType<typeof CmkSuggestions> | null>(null)
const showSuggestions = ref<boolean>(false)

const selectFirstSuggestion = () => {
  if (filteredSuggestions.value.length > 0) {
    const suggestion = filteredSuggestions.value[0]
    if (suggestion) {
      selectSuggestion(suggestion)
    }
  }
}

const selectSuggestion = (suggestion: Suggestion) => {
  inputValue.value = suggestion[0]
  visibleInputValue.value = suggestion[1]
  if (props.resestInputOnAdd) {
    resetVisibleInput()
  }
  emit('select', suggestion[0])
  showSuggestions.value = false
}

const deleteSelection = () => {
  inputValue.value = ''
  resetVisibleInput()
  emit('select', '')
}

const resetVisibleInput = () => {
  visibleInputValue.value = ''
  autocompleterInput.value = ''
}

onMounted(() => {
  if (inputValue.value) {
    visibleInputValue.value = inputValue.value
  }
})

watch(autocompleterOutput, (newValue) => {
  if (newValue === undefined) {
    return
  }
  filteredSuggestions.value = newValue.choices
    .filter((element: Suggestion) => element[0].length > 0 && element[1].length > 0)
    .filter((element: Suggestion) => !props.filterOn.includes(element[0]))
})

const vClickOutside = useClickOutside()
</script>

<template>
  <div v-click-outside="() => (showSuggestions = false)" class="autocomplete">
    <span style="display: flex; align-items: center">
      <input
        :id="props.id ?? 'autocomplete'"
        v-model="visibleInputValue"
        class="item new-item"
        type="text"
        autocomplete="on"
        :size="props.size"
        :placeholder="props.placeholder"
        @keydown.enter.prevent="selectFirstSuggestion"
        @focus="() => (showSuggestions = true)"
        @input="
          (ev: Event) => {
            autocompleterInput = (ev.target as HTMLInputElement).value
            showSuggestions = true
          }
        "
        @keydown.down.prevent="
          () => {
            suggestionsRef?.focus()
            suggestionsRef?.advance()
          }
        "
      />
      <X
        :style="{
          opacity: !!visibleInputValue ? 1 : 0,
          cursor: !!visibleInputValue ? 'pointer' : 'unset'
        }"
        class="item-delete-btn"
        @click="deleteSelection"
      />
    </span>
    <CmkSuggestions
      v-if="filteredSuggestions.length > 0 && !!showSuggestions"
      ref="suggestionsRef"
      :suggestions="
        filteredSuggestions.map((suggestion) => ({ name: suggestion[0], title: suggestion[1] }))
      "
      :on-select="(suggestion) => selectSuggestion([suggestion.name, suggestion.title])"
      :show-filter="false"
    />
  </div>
</template>

<style scoped>
.label-list {
  list-style-type: none;
  padding: 0;
  margin: 0;

  li {
    width: fit-content;
    border-radius: 5px;
    background-color: var(--default-form-element-bg-color);
    margin: 5px 0;
    padding: 2px;
  }
}

table.nform input {
  margin: 0 5px;
  padding: 2px;
}

.item {
  background-color: var(--default-form-element-bg-color);

  &:focus,
  &:active {
    background-color: var(--default-form-element-border-color);
  }
}

.new-item {
  padding: 4px;
}

.error {
  margin: 0;
  padding: 5px;
  background-color: rgb(247, 65, 65);
  color: var(--default-text-color);
  display: block;
}

.item-delete-btn {
  cursor: pointer;
  margin: 0 5px;
  padding: 0;
  border-radius: 50%;
  width: 10px;
  height: 10px;
  border: none;

  &:hover {
    background-color: #c77777;
  }
}

.autocomplete {
  position: relative;
  width: fit-content;
  border-radius: 5px;

  background-color: var(--default-form-element-bg-color);
  margin: 0;
  padding: 0;

  &:focus-within {
    background-color: var(--default-form-element-border-color);
  }
}

.suggestions {
  position: absolute;
  z-index: 1;
  color: var(--default-text-color);
  background-color: var(--default-form-element-bg-color);
  border-radius: 4px;
  max-height: 200px;
  width: 100%;
  overflow-y: auto;
  margin: 0;
  padding: 0;
  list-style-type: none;

  li {
    padding: 4px 8px;
    cursor: pointer;

    &:hover,
    &.selected {
      color: var(--default-select-hover-color);
    }
  }
}
</style>
