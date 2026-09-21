<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

const props = defineProps<{
  placeholder?: TranslatedString
  ariaLabel?: TranslatedString
}>()

const model = defineModel<string>({ default: '' })

const { _t } = usei18n()

const placeholderText = computed(() => props.placeholder ?? _t('Search'))
const ariaLabelText = computed(() => props.ariaLabel ?? _t('Search'))

function onEscape(event: KeyboardEvent): void {
  if (model.value) {
    model.value = ''
    event.stopPropagation()
  }
}
</script>

<template>
  <CmkSearchInput
    v-model="model"
    class="monitoring-filter-search-input"
    inline-search-icon
    :show-submit-button="false"
    :placeholder="placeholderText"
    :aria-label="ariaLabelText"
    @keydown.escape="onEscape"
  />
</template>

<style scoped>
.monitoring-filter-search-input {
  box-sizing: border-box;
  width: 100%;
  margin: 0 0 var(--dimension-3);
}
</style>
