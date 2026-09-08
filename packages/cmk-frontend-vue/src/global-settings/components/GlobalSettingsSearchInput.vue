<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

defineProps<{ placeholder: string }>()

const query = defineModel<string>({ default: '' })
</script>

<template>
  <div class="global-settings-search-input">
    <input
      v-model="query"
      type="search"
      class="global-settings-search-input__field"
      :aria-label="placeholder"
      :placeholder="placeholder"
      autocomplete="off"
    />
    <CmkMultitoneIcon
      v-if="query.length === 0"
      class="global-settings-search-input__icon"
      name="search"
      primary-color="others"
      size="small"
      aria-hidden="true"
    />
    <CmkIconButton
      v-else
      class="global-settings-search-input__clear"
      name="close"
      size="small"
      :title="_t('Clear search')"
      @click="query = ''"
    />
  </div>
</template>

<style scoped>
.global-settings-search-input {
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

.global-settings-search-input__field {
  flex: 1 1 auto;
  min-width: 0;
  height: 100%;
  margin: 0 var(--dimension-4) 0 0;
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

.global-settings-search-input__icon,
.global-settings-search-input__clear {
  flex: 0 0 auto;
  opacity: 0.6;
}

.global-settings-search-input__clear:hover {
  opacity: 1;
}
</style>
