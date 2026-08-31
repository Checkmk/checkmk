<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import CmkSuggestions, {
  ErrorResponse,
  NoSelection,
  Selection,
  SelectionWithTitle,
  type Suggestion,
  type SuggestionValue,
  type Suggestions,
  flattenSuggestions
} from 'cmk-ui-library/components/CmkSuggestions'
import ArrowDown from 'cmk-ui-library/components/graphics/ArrowDown.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import useClickOutside from 'cmk-ui-library/lib/useClickOutside'
import { useFloatingTarget } from 'cmk-ui-library/lib/useFloatingTarget'
import { immediateWatch } from 'cmk-ui-library/lib/watch'
import { PopoverAnchor, PopoverContent, PopoverPortal, PopoverRoot } from 'reka-ui'
import { computed, nextTick, ref, useSlots, useTemplateRef } from 'vue'

import CmkInlineValidation from '../user-input/CmkInlineValidation.vue'
import CmkDropdownButton, { type ButtonVariants } from './CmkDropdownButton.vue'
import TruncateText from './TruncateText.vue'

export interface DropdownOption {
  name: string
  title: string
}

const {
  inputHint = untranslated(''),
  noResultsHint = '',
  disabled = false,
  componentId = null,
  noElementsText = untranslated(''),
  required = false,
  width,
  options,
  label,
  formValidation = false,
  describedBy,
  floating = false
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
  describedBy?: string | undefined
  floating?: boolean
}>()

const selectedOptionPublic = defineModel<string | null>({ default: null })

const vClickOutside = useClickOutside()

const floatingTarget = useFloatingTarget()

const buttonLabel = ref<TranslatedString>(inputHint)
const callbackFilteredErrorMessage = ref<string | null>(null)
const callbackFilteredLoading = ref<boolean>(false)
const internallyDisabled = ref<boolean>(false)

const selectedOption = ref<SuggestionValue>(new NoSelection())

immediateWatch(
  () => ({
    newValue: selectedOptionPublic.value,
    newOptions: options
  }),
  async ({ newValue, newOptions }) => {
    callbackFilteredLoading.value = false
    if (newOptions.type === 'callback-filtered' && newValue !== null) {
      internallyDisabled.value = true
      callbackFilteredLoading.value = true
    }
    const currentSelectionState = await getCurrentSelectionState(newOptions, newValue)
    callbackFilteredLoading.value = false
    internallyDisabled.value = false
    // Only update if the selected option hasn't changed again while awaiting
    if (newValue === selectedOptionPublic.value) {
      buttonLabel.value = currentSelectionState.buttonLabel
      selectedOption.value = currentSelectionState.value
    }
  }
)

/**
 * This function might have a performance impact as it might trigger a callback to fetch
 * suggestions. It should only be called when necessary.
 */
async function getCurrentSelectionState(
  options: Suggestions,
  selected: string | null
): Promise<{ value: SuggestionValue; buttonLabel: TranslatedString }> {
  let currentOptions: Suggestion[]
  switch (options.type) {
    case 'filtered':
    case 'fixed': {
      if (options.suggestions.length === 0) {
        return { value: new NoSelection(), buttonLabel: noElementsText || inputHint }
      } else if (selected === null) {
        return { value: new NoSelection(), buttonLabel: inputHint }
      }
      currentOptions = flattenSuggestions(options.suggestions)
      break
    }
    case 'callback-filtered': {
      if (selected === null) {
        return { value: new NoSelection(), buttonLabel: inputHint }
      }
      const result = await options.querySuggestions(selected)

      if (result instanceof ErrorResponse) {
        callbackFilteredErrorMessage.value = result.error
        return { value: new Selection(selected), buttonLabel: untranslated(selected) }
      } else {
        callbackFilteredErrorMessage.value = null
        currentOptions = flattenSuggestions(result.choices)
      }
      break
    }
  }
  if (currentOptions.length === 0) {
    return { value: new NoSelection(), buttonLabel: noElementsText }
  } else {
    const selectedSuggestion = currentOptions.find((s: Suggestion) => s.name === selected)
    if (selectedSuggestion) {
      if (selectedSuggestion.name === null) {
        return {
          value: new NoSelection(),
          buttonLabel: inputHint
        }
      }
      return {
        value: new SelectionWithTitle(selectedSuggestion.name, selectedSuggestion.title),
        buttonLabel: selectedSuggestion.title
      }
    } else {
      return { value: new Selection(selected), buttonLabel: untranslated(selected) }
    }
  }
}

const canOpenDropdown = computed(() => {
  if (internallyDisabled.value === true) {
    return false
  }
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
const rootRef = ref<HTMLElement | null>(null)

const PREFERRED_MIN_BELOW_PX = 200

// Modern browsers position the list via CSS anchor positioning (see <style>); older ones use the JS fallback.
const supportsAnchorPositioning =
  typeof CSS !== 'undefined' &&
  typeof CSS.supports === 'function' &&
  CSS.supports('anchor-name: --x') &&
  CSS.supports('anchor-scope: all')

const flippedUp = ref(false)

const nonFloatingMaxHeight = supportsAnchorPositioning ? 'none' : `${PREFERRED_MIN_BELOW_PX}px`
// Grace margin kept between the list and the viewport edge.
const VIEWPORT_MARGIN_PX = 40
const floatingCollisionPadding = { top: VIEWPORT_MARGIN_PX, bottom: VIEWPORT_MARGIN_PX }

// Mirrors CmkSuggestions' max-width, which our same-axis max-inline-size would otherwise override.
const SUGGESTIONS_MAX_INLINE_SIZE_PX = 512

// Height and width caps for the anchor-positioned list, updated from JS on open; these fallbacks
// keep it scrollable and width-bounded until then.
const listMaxBlockSize = ref<string>(`calc(100dvh - ${2 * VIEWPORT_MARGIN_PX}px)`)
const listMaxInlineSize = ref<string>(
  `min(${SUGGESTIONS_MAX_INLINE_SIZE_PX}px, calc(100dvw - ${2 * VIEWPORT_MARGIN_PX}px))`
)
// reka-ui provides the collision-aware available height, already less the collision padding above.
// The floor is what lets its flip still fire: a list capped to exactly the room it has never
// collides, so without it the list stays below the button and shrinks to a sliver.
// The var is only set once reka-ui has positioned the list, and an unset one would take the whole
// declaration down with it, so the fallback caps the list until then.
const floatingMaxHeight = `max(${PREFERRED_MIN_BELOW_PX}px, var(--reka-popper-available-height, 500px))`

// Swallow the click-outside fired by the in-flight bubble when open() is
// called from a sibling's click handler.
const suppressNextClickOutside = ref(false)

defineExpose({
  open: () => {
    if (suggestionsShown.value) {
      return
    }
    suppressNextClickOutside.value = true
    showSuggestions()
    // We use setTimeout here instead of nextTick because
    // the reset must outlive the entire click dispatch.
    setTimeout(() => {
      suppressNextClickOutside.value = false
    }, 0)
  },
  focus: () => {
    comboboxButtonRef.value?.focus()
  },
  isOpen: () => suggestionsShown.value
})

function showSuggestions(): void {
  if (!disabled && canOpenDropdown.value) {
    suggestionsShown.value = !suggestionsShown.value
    if (!suggestionsShown.value) {
      return
    }

    nextTick(async () => {
      if (suggestionsRef.value) {
        if (!floating) {
          updateNonFloatingPlacement()
        }
        await suggestionsRef.value.focus()
      }
    })
  }
}

function updateNonFloatingPlacement(): void {
  const listElement = suggestionsRef.value?.$el as HTMLElement | undefined
  const anchor = rootRef.value
  if (!listElement || !anchor) {
    return
  }
  const anchorRect = anchor.getBoundingClientRect()
  const spaceBelow = window.innerHeight - anchorRect.bottom
  const spaceAbove = anchorRect.top
  flippedUp.value = spaceBelow < PREFERRED_MIN_BELOW_PX && spaceAbove > spaceBelow

  // Floored so a cramped side still yields a usable, scrollable list.
  const availableInDirection = (flippedUp.value ? spaceAbove : spaceBelow) - VIEWPORT_MARGIN_PX
  listMaxBlockSize.value = `${Math.max(PREFERRED_MIN_BELOW_PX, availableInDirection)}px`

  // Cap to the room right of the button so a wide list never overflows and hides its scrollbar.
  const roomRightOfButton = window.innerWidth - anchorRect.left - VIEWPORT_MARGIN_PX
  listMaxInlineSize.value = `${Math.min(SUGGESTIONS_MAX_INLINE_SIZE_PX, roomRightOfButton)}px`

  if (supportsAnchorPositioning) {
    // From here the CSS positions the list, keyed on the flippedUp class.
    return
  }
  if (flippedUp.value) {
    listElement.style.bottom = `calc(2 * var(--spacing))`
  } else {
    listElement.style.removeProperty('bottom')
  }
}

function hideSuggestions(): void {
  suggestionsShown.value = false
  comboboxButtonRef.value?.focus()
}

function onClickOutside(): void {
  if (floating) {
    return
  }
  if (suppressNextClickOutside.value) {
    return
  }
  if (suggestionsShown.value) {
    suggestionsShown.value = false
  }
}

function onFloatingOpenChange(open: boolean): void {
  if (!open) {
    suggestionsShown.value = false
  }
}

function onFloatingInteractOutside(event: Event): void {
  const originalEvent = (event as CustomEvent<{ originalEvent: Event }>).detail?.originalEvent
  if (originalEvent?.target instanceof Node && rootRef.value?.contains(originalEvent.target)) {
    event.preventDefault()
  }
}

function handleUpdate(selected: Suggestion | null): void {
  // Only write the model; the internal state syncs back from the watch, so a
  // controlled parent that keeps its value (e.g. an add-control pinned to
  // null) keeps the dropdown unselected and repeated picks emit again.
  selectedOptionPublic.value = selected === null || selected.name === null ? null : selected.name
  callbackFilteredErrorMessage.value = null
  hideSuggestions()
}

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
    ref="rootRef"
    v-click-outside="onClickOutside"
    class="cmk-dropdown"
    :class="{ 'cmk-dropdown__fill': width === 'fill' }"
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
      :aria-invalid="formValidation || undefined"
      :aria-describedby="describedBy"
      :disabled="disabled"
      :multiple-choices-available="canOpenDropdown"
      :value-is-selected="!(selectedOption instanceof NoSelection)"
      :group="group"
      :width="width"
      :class="{ 'cmk-dropdown__validation-error': formValidation }"
      @click="showSuggestions"
    >
      <span v-if="!!slots['button-prefix']" class="cmk-dropdown--button-prefix">
        <slot name="button-prefix"></slot>
      </span>
      <template v-if="callbackFilteredLoading">
        <CmkLoading />
      </template>
      <span v-if="!callbackFilteredLoading && buttonLabel" style="display: contents"
        ><TruncateText :text="buttonLabel" /></span
      ><CmkLabelRequired
        :show="required && selectedOption instanceof NoSelection"
        :space="'before'" />
      <template v-if="!callbackFilteredLoading && !buttonLabel">&nbsp;</template>
      <ArrowDown
        class="cmk-dropdown--arrow"
        :class="{ rotated: suggestionsShown, disabled: disabled || !canOpenDropdown }"
        aria-hidden="true"
    /></CmkDropdownButton>
    <slot name="buttons-end"></slot>
    <CmkSuggestions
      v-if="!!suggestionsShown && !floating"
      ref="suggestionsRef"
      role="option"
      :class="['cmk-dropdown__suggestions', { 'cmk-dropdown__suggestions--flipped': flippedUp }]"
      :suggestions="options"
      :selected-suggestion="selectedOption"
      :no-results-hint="noResultsHint"
      :max-height="nonFloatingMaxHeight"
      @request-close-suggestions="hideSuggestions"
      @select-suggestion="handleUpdate"
    />
    <PopoverRoot
      v-if="floating"
      :open="!!suggestionsShown"
      :modal="false"
      @update:open="onFloatingOpenChange"
    >
      <PopoverAnchor v-bind="rootRef ? { reference: rootRef } : {}" class="cmk-dropdown__anchor" />
      <PopoverPortal :to="floatingTarget ?? 'body'">
        <PopoverContent
          side="bottom"
          align="start"
          :collision-padding="floatingCollisionPadding"
          class="cmk-dropdown__floating"
          :style="{ position: 'relative', zIndex: 'var(--z-index-dropdown-offset)' }"
          @open-auto-focus.prevent
          @close-auto-focus.prevent
          @interact-outside="onFloatingInteractOutside"
        >
          <CmkSuggestions
            ref="suggestionsRef"
            role="option"
            :suggestions="options"
            :selected-suggestion="selectedOption"
            :no-results-hint="noResultsHint"
            :max-height="floatingMaxHeight"
            @request-close-suggestions="hideSuggestions"
            @select-suggestion="handleUpdate"
          />
        </PopoverContent>
      </PopoverPortal>
    </PopoverRoot>
  </div>
</template>

<style scoped>
.cmk-dropdown {
  display: inline-block;
  position: relative;
  white-space: nowrap;
  align-self: flex-start;

  .cmk-dropdown--button-prefix {
    display: flex;
    align-items: center;
    height: 1lh;
  }

  .cmk-dropdown--arrow {
    flex-shrink: 0;
    width: 0.7em;
    color: var(--dropdown-arrow-color);
    margin-left: auto;
    padding: 0 4px;
    margin-top: -1px;

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

.cmk-dropdown__fill {
  width: 100%;
}

.cmk-dropdown__validation-error {
  border: 1px solid var(--inline-error-border-color);
}

.cmk-dropdown__anchor {
  display: contents;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.cmk-dropdown__floating .cmk-suggestions {
  position: static;
  min-width: var(--reka-popper-anchor-width);
}

/* Anchor the list edge to its own button explicitly rather than via position-area, whose block
   sizing fails to clamp once a transformed ancestor becomes the fixed containing block. */
@supports (anchor-name: --x) and (anchor-scope: all) {
  .cmk-dropdown {
    anchor-name: --cmk-dropdown-anchor;

    /* Confine the anchor name so each list tethers to its own button, not a single shared one. */
    anchor-scope: --cmk-dropdown-anchor;
  }

  .cmk-dropdown > .cmk-dropdown__suggestions {
    position: fixed;
    position-anchor: --cmk-dropdown-anchor;
    inset-block-start: anchor(bottom);
    inset-inline-start: anchor(left);
    block-size: fit-content;
    max-block-size: v-bind(listMaxBlockSize);
    min-width: anchor-size(width);
    max-inline-size: v-bind(listMaxInlineSize);
  }

  .cmk-dropdown > .cmk-dropdown__suggestions.cmk-dropdown__suggestions--flipped {
    inset-block: auto anchor(top);
  }
}
</style>
