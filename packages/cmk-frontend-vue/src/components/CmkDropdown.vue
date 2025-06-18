<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, useTemplateRef, nextTick, ref } from 'vue'
import useClickOutside from '@/lib/useClickOutside'
import { immediateWatch } from '@/lib/watch'
import FormRequired from '@/form/private/FormRequired.vue'
import CmkDropdownButton from './CmkDropdownButton.vue'
import CmkSuggestions from './CmkSuggestions.vue'
import { type Suggestions } from './CmkSuggestions.vue'
import ArrowDown from '@/components/graphics/ArrowDown.vue'

export interface DropdownOption {
  name: string
  title: string
}
import { ErrorResponse } from './suggestions'

const {
  inputHint = '',
  noResultsHint = '',
  disabled = false,
  componentId = null,
  noElementsText = '',
  requiredText = '',
  startOfGroup = false,
  width,
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
  startOfGroup?: boolean
  width?: 'wide' | 'default'
}>()

const vClickOutside = useClickOutside()

const selectedOption = defineModel<string | null>('selectedOption', { required: true })
const buttonLabel = ref<string>(inputHint)

immediateWatch(
  () => ({ newOptions: options, newSelectedOption: selectedOption }),
  async ({ newOptions, newSelectedOption }) => {
    async function getDropdownButtonLabel(): Promise<string> {
      // function makes sure that all branches return a value
      if (newSelectedOption.value === null) {
        return inputHint
      }
      if (newOptions.type === 'filtered' || newOptions.type === 'fixed') {
        if (newOptions.suggestions.length === 0) {
          return noElementsText
        } else {
          return (
            newOptions.suggestions.find(({ name }) => name === newSelectedOption.value)?.title ??
            inputHint
          )
        }
      } else {
        if (newOptions.getTitle !== undefined) {
          const result = await newOptions.getTitle(newSelectedOption.value)
          if (result instanceof ErrorResponse) {
            console.error('CmkDropdown: internal: getTtitle returned an error:', result.error)
            return `id: ${newSelectedOption.value}`
          }
          return result
        }
        // return the internal id, if we have no chance to look up the value
        return newSelectedOption.value
      }
    }
    buttonLabel.value = await getDropdownButtonLabel()
  },
  { deep: 2 }
)

const multipleChoicesAvailable = computed(() => {
  if (options.type === 'filtered' || options.type === 'fixed') {
    return options.suggestions.length !== 0
  }
  return true // assume something is available via callback/backend
  // we don't know the number of available suggestions, as this is handled by CmkSuggestions,
  // so we just assume we have something to display, although maybe, we don't have.
})

const suggestionsShown = ref(false)
const suggestionsRef = ref<InstanceType<typeof CmkSuggestions> | null>(null)
const comboboxButtonRef =
  useTemplateRef<InstanceType<typeof CmkDropdownButton>>('comboboxButtonRef')

function showSuggestions(): void {
  if (!disabled && multipleChoicesAvailable.value) {
    suggestionsShown.value = !suggestionsShown.value
    if (!suggestionsShown.value) {
      return
    }
    // eslint-disable-next-line @typescript-eslint/no-floating-promises
    nextTick(async () => {
      if (suggestionsRef.value) {
        const suggestionsRect = suggestionsRef.value.$el.getBoundingClientRect()
        if (window.innerHeight - suggestionsRect.bottom < suggestionsRect.height) {
          suggestionsRef.value.$el.style.bottom = `calc(2 * var(--spacing))`
        } else {
          suggestionsRef.value.$el.style.removeProperty('bottom')
        }
        await suggestionsRef.value.focus()
      }
    })
  }
}

function hideSuggestions(): void {
  suggestionsShown.value = false
  comboboxButtonRef.value?.focus()
}

function handleUpdate(selected: string | null): void {
  selectedOption.value = selected
  hideSuggestions()
}

const maxLabelLength = 60
const truncatedButtonLabel = computed(() =>
  buttonLabel.value.length > maxLabelLength
    ? `${buttonLabel.value.slice(0, maxLabelLength / 2 - 5)}...${buttonLabel.value.slice(-maxLabelLength / 2 + 5)}`
    : buttonLabel.value
)
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
    <CmkDropdownButton
      :id="componentId"
      ref="comboboxButtonRef"
      :aria-label="label"
      :aria-expanded="suggestionsShown"
      :title="buttonLabel.length > maxLabelLength ? buttonLabel : ''"
      :disabled="disabled"
      :multiple-choices-available="multipleChoicesAvailable"
      :value-is-selected="selectedOption !== null"
      :open="suggestionsShown"
      :group="startOfGroup ? 'start' : 'no'"
      :width="width"
      @click="showSuggestions"
    >
      <span class="cmk-dropdown--text"
        >{{ truncatedButtonLabel
        }}<template v-if="requiredText !== '' && selectedOption === null">
          {{ ' ' }}<FormRequired :show="true" :space="'before'" :i18n-required="requiredText"
        /></template>
        <template v-if="!buttonLabel">&nbsp;</template>
      </span>
      <ArrowDown
        class="cmk-dropdown--arrow"
        :class="{ rotated: suggestionsShown, disabled: disabled || !multipleChoicesAvailable }"
    /></CmkDropdownButton>
    <CmkSuggestions
      v-if="!!suggestionsShown"
      ref="suggestionsRef"
      role="option"
      :suggestions="options"
      :selected-option="selectedOption"
      :no-results-hint="noResultsHint"
      @request-close-suggestions="hideSuggestions"
      @update:selected-option="handleUpdate"
    />
  </div>
</template>

<style scoped>
.cmk-dropdown {
  display: inline-block;
  position: relative;
  white-space: nowrap;

  .cmk-dropdown--arrow {
    width: 0.7em;
    /* This replicates the dropdown in checkmk, which useses select2 which
       uses #888 as color by default. The color is not themed there, so we
       also don't theme it. */
    color: #888;
    margin: 0 3px 0 10px;

    &.rotated {
      transform: rotate(180deg);
    }

    &.disabled {
      opacity: 0.4;
    }
  }
}
</style>
