<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { CheckboxIndicator, CheckboxRoot } from 'radix-vue'
import { useId } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import CmkHtml from '@/components/CmkHtml.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'

defineOptions({ inheritAttrs: false })

const value = defineModel<boolean>({ required: false, default: false })

interface CmkCheckboxProps {
  label?: TranslatedString
  padding?: 'top' | 'bottom' | 'both'
  help?: TranslatedString
  externalErrors?: string[]
  disabled?: boolean
  dots?: boolean
}

const { padding = 'both', label, disabled = false } = defineProps<CmkCheckboxProps>()

const id = useId()
</script>

<template>
  <span class="cmk-checkbox__container" v-bind="$attrs">
    <div
      class="cmk-checkbox"
      :class="{
        'cmk-checkbox__pad-top': padding !== 'bottom',
        'cmk-checkbox__pad-bottom': padding !== 'top',
        'cmk-checkbox__disabled': disabled
      }"
    >
      <CheckboxRoot
        :id="id"
        v-model:checked="value"
        class="cmk-checkbox__button"
        :disabled="disabled"
      >
        <CheckboxIndicator class="cmk-checkbox__indicator">
          <svg version="1.1" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
            <g transform="rotate(45,9,9)">
              <path d="m18.5 6.5v5h-7v7h-5v-7h-7v-5h7v-7h5v7z" fill="currentcolor" />
            </g>
          </svg>
        </CheckboxIndicator>
      </CheckboxRoot>
      <template v-if="label">
        <CmkSpace :size="'small'" />
        <CmkLabel :for="id" :help="help" :dots="dots">
          <CmkHtml class="cmk-checkbox__label" :html="label" /> </CmkLabel
      ></template>
    </div>
  </span>
  <CmkInlineValidation :validation="externalErrors"></CmkInlineValidation>
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

  &.cmk-checkbox__pad-top {
    padding-top: 2px;
  }

  &.cmk-checkbox__pad-bottom {
    padding-bottom: 2px;
  }

  .cmk-checkbox__label {
    cursor: pointer;
  }

  &.cmk-checkbox__disabled {
    cursor: not-allowed;
    opacity: 0.6;

    .cmk-checkbox__label {
      cursor: not-allowed;
    }
  }

  .cmk-checkbox__indicator {
    display: flex;
    justify-content: center;
    align-items: center;

    svg {
      width: 8px;
    }
  }
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(.cmk-checkbox__button) {
  background-color: var(--default-form-element-bg-color);
  border: 1px solid var(--default-form-element-bg-color);
  border-radius: 2px;
  height: 14.5px;
  width: 14.5px;
  min-width: 14.5px;
  min-height: 14.5px;
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
}
</style>
