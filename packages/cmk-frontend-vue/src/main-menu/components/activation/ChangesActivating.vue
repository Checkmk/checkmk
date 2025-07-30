<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkProgressbar from '@/components/CmkProgressbar.vue'
import usei18n from '@/lib/i18n'

const { t } = usei18n('changes-app')

defineProps<{
  activatingOnSites: string[] | string | undefined
}>()
</script>

<template>
  <div class="cmk-changes-activating-container">
    <span v-if="typeof activatingOnSites === 'string'" class="cmk-changes-activating-text"
      >{{ t('activating-changes-on', 'Activating changes on ') }}
      {{ "'".concat(activatingOnSites as string).concat("'...") }}</span
    >
    <span v-else class="cmk-changes-activating-text"
      >{{ t('activating-changes', 'Activating changes... ') }}
    </span>
    <span>{{
      t(
        'safely-navigate-away',
        "You can safely navigate away - we'll keep working in the background"
      )
    }}</span>
    <CmkProgressbar max="unknown"></CmkProgressbar>
  </div>
</template>

<style scoped>
.cmk-changes-activating-container {
  display: flex;
  padding: var(--dimension-padding-9) var(--dimension-padding-4);
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: var(--dimension-item-spacing-4);
  align-self: stretch;
  background: var(--ux-theme-4);
}

.cmk-changes-activating-text {
  font-weight: var(--font-weight-bold);
}
</style>
