<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, useTemplateRef } from 'vue'

export type RegexMode = 'regex' | 'text'

defineOptions({ inheritAttrs: false })

const { _t } = usei18n()

const props = defineProps<{
  mode: RegexMode
  label: string
  maxlength?: number
}>()

const text = defineModel<string>({ required: true })

const MAX_LABEL_LENGTH = 60

const placeholder = computed(() =>
  props.mode === 'regex' ? _t('Enter regex (pattern match)') : _t('Enter plain text (single match)')
)

const input = useTemplateRef<HTMLInputElement>('input')

defineExpose({ focus: () => input.value?.focus() })
</script>

<template>
  <div class="form-regex-input">
    <input
      ref="input"
      v-model="text"
      class="form-regex-input__input"
      :aria-label="label"
      :title="text.length > MAX_LABEL_LENGTH ? text : ''"
      :placeholder="placeholder"
      :maxlength="maxlength"
      v-bind="$attrs"
    />
    <button v-if="text" type="button" class="form-regex-input__clear" @click="text = ''">
      <CmkIcon name="close" size="small" />
    </button>
  </div>
</template>

<style scoped>
.form-regex-input {
  position: relative;
  width: 196px;
  display: inline-block;
}

.form-regex-input__input {
  border: 1px solid var(--default-form-element-border-color);
  padding: 0 12px 0 3px;
  height: 20px;
  border-left: 0;
  border-radius: 0 var(--border-radius) var(--border-radius) 0;
  font-size: var(--font-size-normal);
  background-color: var(--ux-theme-5);
  position: relative;
  color: var(--font-color);
  width: 175px;
}

.form-regex-input__input:focus {
  border-color: var(--default-form-element-border-color);
  background-color: var(--ux-theme-5);
}

.form-regex-input__clear {
  position: absolute;
  right: 1.2em;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  padding: 0;
  margin: 0;
  cursor: pointer;
  height: 1.5em;
  width: 1.5em;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
