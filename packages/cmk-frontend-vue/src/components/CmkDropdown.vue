<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Ref, computed, nextTick, ref, watch } from 'vue'
import CmkButton from './CmkButton.vue'
import useClickOutside from '@/lib/useClickOutside'
import FormRequired from '@/form/private/FormRequired.vue'
import ArrowDown from '@/components/graphics/ArrowDown.vue'
import CmkSuggestions from './CmkSuggestions.vue'

export interface DropdownOption {
  name: string
  title: string
}

const {
  inputHint = '',
  noResultsHint = '',
  disabled = false,
  componentId = null,
  noElementsText = '',
  requiredText = '',
  options,
  showFilter,
  label
} = defineProps<{
  options: DropdownOption[]
  showFilter: boolean
  inputHint?: string
  noResultsHint?: string
  disabled?: boolean
  componentId?: string | null
  noElementsText?: string
  requiredText?: string
  label: string
}>()

const vClickOutside = useClickOutside()

const selectedOption = defineModel<string | null>('selectedOption', { required: true })
const dropdownButtonLabel = computed(() =>
  options.length === 0
    ? noElementsText
    : (options.find(({ name }) => name === selectedOption.value)?.title ?? inputHint)
)

const noChoiceAvailable = computed(() => options.length === 0)

const suggestionsShown = ref(false)
const suggestionsRef = ref<InstanceType<typeof CmkSuggestions> | null>(null)
const comboboxButtonRef = ref<HTMLButtonElement | null>(null)

const filterString = ref('')
const filteredOptions = ref<number[]>(options.map((_, index) => index))
const selectedSuggestionOptionIndex: Ref<number | null> = ref(options.length > 0 ? 0 : null)

watch(filterString, (newFilterString) => {
  filteredOptions.value = options
    .map((option, index) => ({
      option,
      index
    }))
    .filter(({ option }) => option.title.toLowerCase().includes(newFilterString.toLowerCase()))
    .map(({ index }) => index)
  selectedSuggestionOptionIndex.value = filteredOptions.value[0] ?? null
})

function showSuggestions(): void {
  if (!disabled && !noChoiceAvailable.value) {
    suggestionsShown.value = !suggestionsShown.value
    if (!suggestionsShown.value) {
      return
    }
    filterString.value = ''
    filteredOptions.value = options.map((_, index) => index)
    selectedSuggestionOptionIndex.value = filteredOptions.value[0] ?? null
    // eslint-disable-next-line @typescript-eslint/no-floating-promises
    nextTick(() => {
      if (suggestionsRef.value) {
        const suggestionsRect = suggestionsRef.value.$el.getBoundingClientRect()
        if (window.innerHeight - suggestionsRect.bottom < suggestionsRect.height) {
          suggestionsRef.value.$el.style.bottom = `calc(2 * var(--spacing))`
        } else {
          suggestionsRef.value.$el.style.removeProperty('bottom')
        }
        suggestionsRef.value.focus()
      }
    })
  }
}

function hideSuggestions(): void {
  suggestionsShown.value = false
  comboboxButtonRef.value?.focus()
}

function selectOption(option: DropdownOption): void {
  selectedOption.value = option.name
  hideSuggestions()
}
</script>

<template>
  <div
    v-click-outside="
      () => {
        if (suggestionsShown) suggestionsShown = false
      }
    "
    class="cmk-dropdown"
  >
    <CmkButton
      :id="componentId"
      ref="comboboxButtonRef"
      role="combobox"
      :aria-label="label"
      :aria-expanded="suggestionsShown"
      class="cmk-dropdown__button"
      :class="{
        disabled,
        no_choices: noChoiceAvailable,
        no_value: selectedOption === null
      }"
      :variant="'transparent'"
      @click.prevent="showSuggestions"
    >
      {{ dropdownButtonLabel
      }}<template v-if="requiredText !== '' && selectedOption === null">
        {{ ' '
        }}<FormRequired :show="true" :space="'before'" :i18n-required="requiredText" /></template
      ><ArrowDown class="cmk-dropdown__button_arrow" />
    </CmkButton>
    <CmkSuggestions
      v-if="!!suggestionsShown"
      ref="suggestionsRef"
      role="option"
      :suggestions="options"
      :on-select="selectOption"
      :no-results-hint="noResultsHint"
      :show-filter="showFilter"
      @keydown.escape.prevent="hideSuggestions"
      @keydown.tab.prevent="hideSuggestions"
    />
  </div>
</template>

<style scoped>
.cmk-dropdown {
  display: inline-block;
  position: relative;
  white-space: nowrap;
}

.cmk-dropdown__button {
  cursor: pointer;
  background-color: var(--default-form-element-bg-color);
  margin: 0;
  padding: 3px 2.5em 4px 6px;
  vertical-align: baseline;

  .cmk-dropdown__button_arrow {
    position: absolute;
    right: 6px;
    top: 50%;
    transform: translateY(-50%);
  }

  &:hover {
    background-color: var(--input-hover-bg-color);
  }

  &.disabled {
    cursor: auto;
    color: var(--font-color-dimmed);
    &:hover {
      background-color: var(--default-form-element-bg-color);
    }
  }

  &.no_value {
    color: var(--font-color-dimmed);

    > .cmk-dropdown__button_arrow {
      color: var(--font-color);
    }
  }

  &.no_choices {
    cursor: auto;
    &:hover {
      background-color: var(--default-form-element-bg-color);
    }
    > .cmk-dropdown__button_arrow {
      color: var(--font-color-dimmed);
    }
  }
}
</style>
