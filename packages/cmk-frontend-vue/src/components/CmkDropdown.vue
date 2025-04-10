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
import { type Suggestions } from './CmkSuggestions.vue'

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
  label
} = defineProps<{
  options: Suggestions
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
  options.suggestions.length === 0
    ? noElementsText
    : (options.suggestions.find(({ name }) => name === selectedOption.value)?.title ?? inputHint)
)

const multipleChoicesAvailable = computed(() => options.suggestions.length !== 0)

const suggestionsShown = ref(false)
const suggestionsRef = ref<InstanceType<typeof CmkSuggestions> | null>(null)
const comboboxButtonRef = ref<HTMLButtonElement | null>(null)

const filterString = ref('')
const filteredOptions = ref<number[]>(options.suggestions.map((_, index) => index))
const selectedSuggestionOptionIndex: Ref<number | null> = ref(
  options.suggestions.length > 0 ? 0 : null
)

watch(filterString, (newFilterString) => {
  filteredOptions.value = options.suggestions
    .map((option, index) => ({
      option,
      index
    }))
    .filter(({ option }) => option.title.toLowerCase().includes(newFilterString.toLowerCase()))
    .map(({ index }) => index)
  selectedSuggestionOptionIndex.value = filteredOptions.value[0] ?? null
})

function showSuggestions(): void {
  if (!disabled && multipleChoicesAvailable.value) {
    suggestionsShown.value = !suggestionsShown.value
    if (!suggestionsShown.value) {
      return
    }
    filterString.value = ''
    filteredOptions.value = options.suggestions.map((_, index) => index)
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
    :class="{
      'cmk-dropdown-suggestions-shown': suggestionsShown
    }"
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
        no_choices: !multipleChoicesAvailable,
        no_value: selectedOption === null
      }"
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
      :no-results-hint="noResultsHint"
      @select="selectOption"
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

.cmk-dropdown-suggestions-shown {
  .cmk-dropdown__button_arrow {
    transform: rotate(180deg);
  }
}

.cmk-dropdown__button {
  height: var(--form-field-height);
  margin: 0;
  padding: 3px 1.9em 4px 6px;
  vertical-align: baseline;
  background-color: var(--default-form-element-bg-color);
  border: none;
  font-weight: var(--font-weight-default);
  cursor: pointer;

  .cmk-dropdown__button_arrow {
    position: absolute;
    right: 7px;
    width: 0.7em;
    /* This replicates the dropdown in checkmk, which useses select2 which
       uses #888 as color by default. The color is not themed there, so we
       also don't theme it. */
    color: #888;
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
      opacity: 0.4;
    }
  }
}
</style>
