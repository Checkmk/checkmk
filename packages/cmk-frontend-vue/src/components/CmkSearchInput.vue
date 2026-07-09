<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'

import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkIconButton from '@/components/CmkIconButton.vue'

const { _t } = usei18n()

defineProps<{
  placeholder: string
}>()

const query = defineModel<string>({ default: '' })

const emit = defineEmits<{
  search: [query: string]
}>()

const input = useTemplateRef<HTMLInputElement>('input')

defineExpose({
  focus: () => {
    input.value?.focus()
    input.value?.select()
  }
})

function submit(): void {
  emit('search', query.value)
}

function clear(): void {
  query.value = ''
  emit('search', '')
}
</script>

<template>
  <div class="cmk-search-input">
    <CmkMultitoneIcon
      class="cmk-search-input__icon"
      name="search"
      primary-color="others"
      size="small"
      aria-hidden="true"
    />
    <input
      ref="input"
      v-model="query"
      type="search"
      role="searchbox"
      class="cmk-search-input__field"
      :aria-label="placeholder"
      :placeholder="placeholder"
      autocomplete="off"
      @keydown.enter="submit"
    />
    <CmkIconButton
      class="cmk-search-input__clear"
      :class="{ 'cmk-search-input__clear--hidden': query.length === 0 }"
      name="close"
      size="small"
      :title="_t('Clear search')"
      @click="clear"
    />
  </div>
</template>

<style scoped>
.cmk-search-input {
  display: flex;
  align-items: center;
  height: 27px;
  padding: 0 var(--spacing);
  background-color: var(--default-form-element-bg-color);
  border: 1px solid var(--default-form-element-border-color);
  border-radius: var(--border-radius);

  &:focus-within {
    border-color: var(--success);
  }
}

.cmk-search-input__icon {
  flex: 0 0 auto;
  opacity: 0.6;
}

.cmk-search-input__field {
  flex: 1 1 auto;
  height: 100%;
  margin: 0 var(--dimension-4);
  padding: 0;
  background: transparent;
  border: 0;

  &:focus {
    outline: none;
  }

  &::-webkit-search-cancel-button {
    appearance: none;
  }
}

.cmk-search-input__clear {
  flex: 0 0 auto;
  opacity: 0.6;

  &:hover {
    opacity: 1;
  }
}

.cmk-search-input__clear--hidden {
  visibility: hidden;
  pointer-events: none;
}
</style>
