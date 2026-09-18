<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="AllowIndeterminate extends boolean = false">
import CmkHtml from 'cmk-ui-library/components/CmkHtml.vue'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkSpace from 'cmk-ui-library/components/CmkSpace.vue'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import useId from 'cmk-ui-library/lib/useId'
import { CheckboxIndicator, CheckboxRoot } from 'reka-ui'
import { computed } from 'vue'

defineOptions({ inheritAttrs: false })

type CheckboxValue = AllowIndeterminate extends true ? boolean | 'indeterminate' : boolean

const value = defineModel<CheckboxValue>({ required: false, default: false })

const {
  padding = 'both',
  label,
  ariaLabel,
  labelPosition = 'right',
  disabled = false,
  externalErrors
} = defineProps<{
  label?: TranslatedString
  /**
   * Accessible name for the checkbox to be used when no visible `label` is rendered
   * (e.g. a row-select checkbox in a table).
   */
  ariaLabel?: TranslatedString
  labelPosition?: 'left' | 'right'
  padding?: 'top' | 'bottom' | 'both'
  help?: TranslatedString
  externalErrors?: string[]
  disabled?: boolean
  dots?: boolean
  allowIndeterminate?: AllowIndeterminate
}>()

defineSlots<{
  /**
   * Replaces the `label` text inside the `<label>`, for a label that needs markup rather
   * than a string. It becomes the checkbox's accessible name, so keep it to phrasing
   * content; anything interactive in here has to stop its own click from reaching the
   * label, or it toggles the checkbox as well.
   */
  label?: () => unknown
  /**
   * Content belonging to the checkbox, rendered under the label and aligned with it - a
   * dependent input, a hint. It sits outside the `<label>`, so it neither joins the
   * accessible name nor toggles the checkbox when clicked.
   */
  default?: () => unknown
}>()

const id = useId()

const hasValidationErrors = computed(() => {
  return externalErrors && externalErrors.length > 0
})
</script>

<template>
  <span class="cmk-checkbox__container" v-bind="$attrs">
    <div
      class="cmk-checkbox"
      :class="{
        'cmk-checkbox__pad-top': padding !== 'bottom',
        'cmk-checkbox__pad-bottom': padding !== 'top',
        'cmk-checkbox__disabled': disabled,
        'cmk-checkbox--label-left': labelPosition === 'left',
        'cmk-checkbox--stacked': !!$slots.default
      }"
    >
      <CheckboxRoot
        :id="id"
        v-model="value"
        class="cmk-checkbox__button"
        :class="{ 'cmk-checkbox__button--error': hasValidationErrors }"
        :disabled="disabled"
        :aria-label="ariaLabel"
      >
        <CheckboxIndicator class="cmk-checkbox__indicator">
          <span v-if="value === 'indeterminate'" class="cmk-checkbox__dash" />
          <svg v-else version="1.1" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
            <g transform="rotate(45,9,9)">
              <path d="m18.5 6.5v5h-7v7h-5v-7h-7v-5h7v-7h5v7z" fill="currentcolor" />
            </g>
          </svg>
        </CheckboxIndicator>
      </CheckboxRoot>
      <template v-if="label || $slots.label || $slots.default">
        <CmkSpace :size="'small'" />
        <div class="cmk-checkbox__column">
          <CmkLabel
            v-if="label || $slots.label"
            :for="id"
            :help="help"
            :dots="dots"
            :grow="labelPosition === 'left'"
          >
            <slot name="label"><CmkHtml class="cmk-checkbox__label" :html="label" /></slot>
          </CmkLabel>
          <div v-if="$slots.default" class="cmk-checkbox__extra"><slot /></div>
        </div>
      </template>
      <CmkInlineValidation :validation="externalErrors"></CmkInlineValidation>
    </div>
  </span>
</template>

<style scoped>
span {
  vertical-align: middle;

  &.cmk-checkbox__container {
    max-width: 100%;
    display: inline-block;
  }
}

.cmk-checkbox {
  display: flex;
  align-items: center;

  &.cmk-checkbox__pad-top {
    padding-top: 2px;
  }

  &.cmk-checkbox__pad-bottom {
    padding-bottom: 2px;
  }

  /* Stacks the label and any slotted content, so the latter lines up with the label text
     rather than with the box. */
  .cmk-checkbox__column {
    display: flex;
    flex-direction: column;
    min-width: 0;
    gap: var(--dimension-3);
  }

  /* Only where content stacks: put the box on the first line instead of centring it
     against a column taller than itself. Callers passing just a label keep the centring. */
  &.cmk-checkbox--stacked {
    align-items: flex-start;
  }

  .cmk-checkbox__label {
    cursor: pointer;
    padding-right: 2px;
  }

  &.cmk-checkbox__disabled {
    cursor: not-allowed;
    opacity: 0.6;

    .cmk-checkbox__label {
      cursor: not-allowed;
    }
  }

  &.cmk-checkbox--label-left {
    flex-direction: row-reverse;
    align-items: flex-start;

    .cmk-checkbox__label {
      vertical-align: baseline;
    }
  }

  .cmk-checkbox__indicator {
    display: flex;
    justify-content: center;
    align-items: center;

    svg {
      width: 9px;
    }

    .cmk-checkbox__dash {
      width: 8px;
      height: 2px;
      background: currentcolor;
      border-radius: 1px;
    }
  }
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(.cmk-checkbox__button) {
  background-color: var(--default-form-element-bg-color);
  border: 1px solid var(--default-form-element-bg-color);
  border-radius: 2px;
  height: 15px;
  width: 15px;
  min-width: 15px;
  min-height: 15px;
  box-shadow: none; /* disable active/focus style of button */
  padding: 0;
  margin: 0;
  vertical-align: middle; /* otherwise will jump without cmk-frontend styles when checked/unchecked */

  .cmk-checkbox:not(.cmk-checkbox__disabled) & {
    &:hover {
      cursor: pointer;
      background-color: var(--input-hover-bg-color);
    }
  }

  .cmk-checkbox.cmk-checkbox__disabled & {
    cursor: not-allowed;
  }

  .cmk-checkbox.cmk-checkbox__disabled & > .cmk-checkbox__label {
    cursor: not-allowed;
  }

  &.cmk-checkbox__button--error {
    border: 1px solid var(--inline-error-border-color);
  }

  &:focus-visible {
    outline: revert;
  }
}
</style>
