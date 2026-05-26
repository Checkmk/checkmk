<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import BaseCell from './BaseCell.vue'

const value = defineModel<boolean>({ required: false, default: false })
</script>

<template>
  <BaseCell class="monitoring-checkbox-cell">
    <template #default>
      <CmkCheckbox v-model="value"></CmkCheckbox>
    </template>
  </BaseCell>
</template>

<style scoped>
/* stylelint-disable selector-pseudo-class-no-unknown */
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.monitoring-checkbox-cell :deep(.monitoring-highlight-wrapper) {
  margin: 0;
  padding: var(--dimension-2) var(--dimension-3);
}
</style>
