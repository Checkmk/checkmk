<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, nextTick, ref, useTemplateRef } from 'vue'

import { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'
import useClickOutside from '@/lib/useClickOutside'
import useId from '@/lib/useId'
import { immediateWatch } from '@/lib/watch'

import CmkSuggestions, {
  NoSelection,
  SelectionWithTitle,
  type Suggestion,
  type SuggestionValue,
  type Suggestions,
  flattenSuggestions
} from '@/components/CmkSuggestions'
import ArrowDown from '@/components/graphics/ArrowDown.vue'

const {
  options,
  label,
  inputHint = untranslated(''),
  disabled = false,
  noResultsHint = '',
  staticLabel = false
} = defineProps<{
  /** Only `fixed` and `filtered` sources are supported. */
  options: Suggestions
  label: TranslatedString
  inputHint?: TranslatedString
  disabled?: boolean
  noResultsHint?: string
  /** Always shows `inputHint`. */
  staticLabel?: boolean
}>()

const selectedName = defineModel<string | null>({ default: null })

defineSlots<{
  /** Per-option content, forwarded to CmkSuggestions; defaults to the suggestion title. */
  option?: (props: { suggestion: Suggestion }) => unknown
}>()

const vClickOutside = useClickOutside()

const open = ref(false)
const popupId = useId()
const selectedOption = ref<SuggestionValue>(new NoSelection())
const buttonLabel = ref<TranslatedString>(inputHint)

// Don't open when there is nothing to show: no options and no fallback hint.
const canOpen = computed(
  () =>
    (options.type !== 'fixed' && options.type !== 'filtered') ||
    options.suggestions.length > 0 ||
    noResultsHint !== ''
)

const suggestionsRef = ref<InstanceType<typeof CmkSuggestions> | null>(null)
const triggerRef = useTemplateRef<HTMLButtonElement>('triggerRef')

// Resolve the selected name to its display title for the trigger label.
immediateWatch(
  () => ({ name: selectedName.value, opts: options }),
  ({ name, opts }) => {
    if (name === null || (opts.type !== 'fixed' && opts.type !== 'filtered')) {
      selectedOption.value = new NoSelection()
      buttonLabel.value = inputHint
      return
    }
    const found = flattenSuggestions(opts.suggestions).find((s) => s.name === name)
    if (found && found.name !== null) {
      selectedOption.value = new SelectionWithTitle(found.name, found.title)
      buttonLabel.value = staticLabel ? inputHint : found.title
    } else {
      selectedOption.value = new NoSelection()
      buttonLabel.value = inputHint
    }
  }
)

function toggle(): void {
  if (disabled || !canOpen.value) {
    return
  }
  open.value = !open.value
  if (!open.value) {
    return
  }
  void nextTick(async () => {
    if (suggestionsRef.value) {
      // Flip the popup upward when there is not enough room below the trigger.
      const rect = suggestionsRef.value.$el.getBoundingClientRect()
      if (window.innerHeight - rect.bottom < rect.height) {
        suggestionsRef.value.$el.style.bottom = `calc(2 * var(--spacing))`
      } else {
        suggestionsRef.value.$el.style.removeProperty('bottom')
      }
      await suggestionsRef.value.focus()
    }
  })
}

function close(): void {
  open.value = false
  triggerRef.value?.focus()
}

function onClickOutside(): void {
  if (open.value) {
    open.value = false
  }
}

function handleSelect(selected: Suggestion | null): void {
  selectedName.value = selected === null || selected.name === null ? null : selected.name
  close()
}
</script>

<template>
  <div v-click-outside="onClickOutside" class="cmk-chip-select">
    <button
      ref="triggerRef"
      type="button"
      role="combobox"
      class="cmk-chip-select__trigger"
      :class="{ 'cmk-chip-select__trigger--disabled': disabled }"
      :aria-label="label"
      aria-haspopup="listbox"
      :aria-expanded="open"
      :aria-controls="open ? popupId : undefined"
      :disabled="disabled"
      @click.prevent="toggle"
    >
      <span class="cmk-chip-select__label">{{ buttonLabel }}</span>
      <span class="cmk-chip-select__caret">
        <ArrowDown
          class="cmk-chip-select__arrow"
          :class="{ 'cmk-chip-select__arrow--open': open }"
          aria-hidden="true"
        />
      </span>
    </button>
    <CmkSuggestions
      v-if="open"
      :id="popupId"
      ref="suggestionsRef"
      role="option"
      :suggestions="options"
      :selected-suggestion="selectedOption"
      :mark-selected="true"
      :no-results-hint="noResultsHint"
      @select-suggestion="handleSelect"
      @request-close-suggestions="close"
    >
      <template v-if="$slots.option" #option="slotProps">
        <slot name="option" v-bind="slotProps" />
      </template>
    </CmkSuggestions>
  </div>
</template>

<style scoped>
.cmk-chip-select {
  display: inline-block;
  position: relative;

  /* Theme the shared CmkSuggestions popup via its custom-property hooks (no :deep needed). */
  --cmk-suggestions-background: var(--ux-theme-5);
  --cmk-suggestions-border-color: var(--button-optional-border-color);
  --cmk-suggestions-item-active-color: var(--font-color);
  --cmk-suggestions-item-hover-background: var(--input-hover-bg-color);
}

/* Split button styled like CmkButton's "optional" variant. */
.cmk-chip-select__trigger {
  display: inline-flex;
  align-items: stretch;
  height: var(--form-field-height);
  margin: 0;
  padding: 0;
  background-color: var(--default-button-optional-color);
  border: 1px solid var(--button-optional-border-color);
  border-radius: 9999px;
  color: var(--button-optional-text-color);
  font-weight: var(--font-weight-default);
  font-size: var(--font-size-normal);
  cursor: pointer;
  overflow: hidden;
}

.cmk-chip-select__trigger:hover:not(.cmk-chip-select__trigger--disabled) {
  background-color: color-mix(in srgb, var(--default-button-optional-color) 90%, var(--white) 10%);
}

.cmk-chip-select__trigger--disabled {
  cursor: auto;
  opacity: 0.5;
}

.cmk-chip-select__label {
  display: flex;
  align-items: center;
  padding: 0 var(--dimension-4);
}

.cmk-chip-select__caret {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 var(--dimension-4);
  border-left: 1px solid var(--button-optional-border-color);
}

.cmk-chip-select__arrow {
  width: 0.7em;
}

.cmk-chip-select__arrow--open {
  transform: scaleY(-1);
}
</style>
