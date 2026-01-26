<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from '@/lib/i18nString'

import CmkHelpText from '@/components/CmkHelpText.vue'

defineProps<{
  title: TranslatedString
  helpText?: TranslatedString
}>()
</script>

<template>
  <span class="db-catalog-panel-header">
    <span class="db-catalog-panel-header__text">{{ title }}</span>
    <span v-if="helpText" class="db-catalog-panel-header__help">
      <CmkHelpText :help="helpText" />
    </span>
  </span>
</template>

<style scoped>
.db-catalog-panel-header__help {
  margin-left: var(--spacing);
}
</style>
