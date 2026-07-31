<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdownButton from 'cmk-ui-library/components/CmkDropdown/CmkDropdownButton.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

const emit = defineEmits<{
  (e: 'clear'): void
}>()
</script>

<template>
  <CmkDropdownButton
    class="metric-backend-dropdown-clear-button"
    group="end"
    :aria-label="_t('Clear selection')"
    @click="emit('clear')"
  >
    <CmkIcon name="close" size="small" />
  </CmkDropdownButton>
</template>

<style scoped>
.metric-backend-dropdown-clear-button {
  align-items: center;
  padding-top: 0;
  padding-bottom: 1px;
  vertical-align: bottom;
}
</style>
