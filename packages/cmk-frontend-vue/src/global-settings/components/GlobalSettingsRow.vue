<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

defineProps<{
  label: TranslatedString
  help?: TranslatedString
}>()
</script>

<template>
  <div class="global-settings-row">
    <div class="global-settings-row__label">
      <CmkLabel :help="help" dots grow>{{ label }}</CmkLabel>
    </div>
    <div class="global-settings-row__value">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.global-settings-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 4px 0;
}

.global-settings-row__label {
  display: flex;
  flex: 0 1 var(--global-settings-row-label-width, 240px);
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
}

.global-settings-row__value {
  flex: 1 1 0;
  min-width: 0;
}
</style>
