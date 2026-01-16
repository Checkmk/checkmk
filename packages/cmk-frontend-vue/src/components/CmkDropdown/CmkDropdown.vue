<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, nextTick, ref, useSlots, useTemplateRef } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'
import useClickOutside from '@/lib/useClickOutside'
import { immediateWatch } from '@/lib/watch'

import CmkSuggestions, {
  ErrorResponse,
  type Suggestion,
  type Suggestions
} from '@/components/CmkSuggestions'
import ArrowDown from '@/components/graphics/ArrowDown.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

import CmkInlineValidation from '../user-input/CmkInlineValidation.vue'
import CmkDropdownButton, { type ButtonVariants } from './CmkDropdownButton.vue'

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
  required = false,
  width,
  options,
  label,
  formValidation = false
} = defineProps<{
  options: Suggestions
  inputHint?: TranslatedString
  noResultsHint?: TranslatedString
  disabled?: boolean
  componentId?: string | null
  noElementsText?: TranslatedString
  required?: boolean
  label: TranslatedString
  width?: ButtonVariants['width']
  formValidation?: boolean
}>()

const vClickOutside = useClickOutside()

const selectedOption = defineModel<string | null>('selectedOption', { required: true })
const buttonLabel = ref<string>(inputHint)
const callbackFilteredErrorMessage = ref<string | null>(null)

immediateWatch(
  () => ({
    newValue: selectedOption.value,
    newOptions: options
  }),
  async ({ newValue, newOptions }) => {
    const label = await getButtonLabel(newOptions, newValue)
    // Only update if the selected option hasn't changed again while awaiting
    if (newValue === selectedOption.value) {
      buttonLabel.value = label
    }
  }
)

/**
 * This function might have a performance impact as it might trigger a callback to fetch
 * suggestions. It should only be called when necessary.
 */
async function getButtonLabel(options: Suggestions, selected: string | null): Promise<string> {
  let currentOptions: Suggestion[]
  switch (options.type) {
    case 'filtered':
    case 'fixed': {
      if (options.suggestions.length === 0) {
        return noElementsText ?? inputHint
      } else if (selected === null) {
        return inputHint
      }
      currentOptions = options.suggestions
      break
    }
    case 'callback-filtered': {
      if (selected === null) {
        return inputHint
      }
      const result = await options.querySuggestions(selected)
      if (result instanceof ErrorResponse) {
        callbackFilteredErrorMessage.value = result.error
        return selected
      } else {
        callbackFilteredErrorMessage.value = null
        currentOptions = result.choices
      }
      break
    }
  }
  if (currentOptions.length === 0) {
    return noElementsText
  } else {
    const selectedSuggestion = currentOptions.find((s: Suggestion) => s.name === selected)
    return selectedSuggestion ? selectedSuggestion.title : selected
  }
}

const canOpenDropdown = computed(() => {
  if (options.type === 'filtered' || options.type === 'fixed') {
    if (!noResultsHint && options.suggestions.length === 0) {
      return false
    }
    return true
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
  if (!disabled && canOpenDropdown.value) {
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

function handleUpdate(selected: Suggestion | null): void {
  selectedOption.value = selected?.name || null
  callbackFilteredErrorMessage.value = null
  hideSuggestions()
}

const maxLabelLength = 60
const truncatedButtonLabel = computed(() =>
  buttonLabel.value.length > maxLabelLength
    ? `${buttonLabel.value.slice(0, maxLabelLength / 2 - 5)}...${buttonLabel.value.slice(-maxLabelLength / 2 + 5)}`
    : buttonLabel.value
)

const slots = useSlots()
const group = computed<ButtonVariants['group']>(() => {
  const hasButtonsStart = !!slots['buttons-start']
  const hasButtonsEnd = !!slots['buttons-end']
  if (hasButtonsStart && hasButtonsEnd) {
    return 'center'
  } else if (hasButtonsStart) {
    return 'end'
  } else if (hasButtonsEnd) {
    return 'start'
  } else {
    return 'no'
  }
})
</script>

<template>
  <div
    v-click-outside="
      () => {
        if (suggestionsShown) suggestionsShown = false
      }
    "
    class="cmk-dropdown"
    :class="{ 'cmk-dropdown__max-width': width === 'max' }"
  >
    <CmkInlineValidation
      v-if="callbackFilteredErrorMessage !== null"
      :validation="[callbackFilteredErrorMessage]"
    ></CmkInlineValidation>
    <slot name="buttons-start"></slot>
    <CmkDropdownButton
      v-bind="componentId!! ? { id: componentId } : {}"
      ref="comboboxButtonRef"
      :aria-label="label"
      :aria-expanded="suggestionsShown"
      :title="buttonLabel.length > maxLabelLength ? buttonLabel : ''"
      :disabled="disabled"
      :multiple-choices-available="canOpenDropdown"
      :value-is-selected="selectedOption !== null"
      :group="group"
      :width="width"
      :class="{ 'cmk-dropdown__validation-error': formValidation }"
      @click="showSuggestions"
    >
      <span class="cmk-dropdown--text"
        >{{ truncatedButtonLabel
        }}<CmkLabelRequired :show="required && selectedOption === null" :space="'before'" />
        <template v-if="!buttonLabel">&nbsp;</template>
      </span>
      <ArrowDown
        class="cmk-dropdown--arrow"
        :class="{ rotated: suggestionsShown, disabled: disabled || !canOpenDropdown }"
    /></CmkDropdownButton>
    <slot name="buttons-end"></slot>
    <CmkSuggestions
      v-if="!!suggestionsShown"
      ref="suggestionsRef"
      role="option"
      :suggestions="options"
      :selected-suggestion="selectedOption"
      :no-results-hint="noResultsHint"
      @request-close-suggestions="hideSuggestions"
      @select-suggestion="handleUpdate"
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
    color: var(--dropdown-arrow-color);
    margin: 0 3px 0 10px;

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    &.rotated {
      transform: rotate(180deg);
    }

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    &.disabled {
      opacity: 0.4;
    }
  }
}

.cmk-dropdown__max-width {
  width: 100%;
}

.cmk-dropdown__validation-error {
  border: 1px solid var(--inline-error-border-color);
}
</style>
