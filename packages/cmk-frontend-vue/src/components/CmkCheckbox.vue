<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { CheckboxIndicator, CheckboxRoot } from 'radix-vue'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkHtml from '@/components/CmkHtml.vue'
const value = defineModel<boolean>({ required: false, default: false })

interface CmkCheckboxProps {
  label?: string
}

const props = defineProps<CmkCheckboxProps>()
</script>

<template>
  <label class="cmk-checkbox">
    <CheckboxRoot v-model:checked="value" class="cmk-checkbox__button">
      <CheckboxIndicator class="cmk-checkbox__indicator">
        <svg version="1.1" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
          <g transform="rotate(45,9,9)">
            <path d="m18.5 6.5v5h-7v7h-5v-7h-7v-5h7v-7h5v7z" fill="currentcolor" />
          </g>
        </svg>
      </CheckboxIndicator>
    </CheckboxRoot>
    <span v-if="props.label"><CmkSpace size="small" /><CmkHtml :html="label" /></span>
  </label>
</template>

<style scoped>
.cmk-checkbox {
  cursor: pointer;
  display: inline-block;
  padding: 2px 0;

  & :deep(.cmk-checkbox__button) {
    background-color: var(--default-form-element-bg-color);
    border: 1px solid var(--default-form-element-bg-color);
    border-radius: 2px;
    height: 14.5px;
    width: 14.5px;

    box-shadow: none; /* disable active/focus style of button */
    padding: 0;
    margin: 0;
    vertical-align: middle; /* otherwise will jump without cmk-frontend styles when checked/unchecked */
  }

  &:hover :deep(.cmk-checkbox__button) {
    background-color: var(--input-hover-bg-color);
  }

  .cmk-checkbox__indicator {
    display: flex;
    justify-content: center;
    align-items: center;

    svg {
      width: 8px;
    }
  }

  span {
    vertical-align: middle;
  }
}
</style>
