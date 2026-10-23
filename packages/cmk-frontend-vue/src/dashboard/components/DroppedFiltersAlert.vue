<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

defineProps<{
  // Translated by the server, which names the filters.
  warning: string
}>()
</script>

<template>
  <div class="db-dropped-filters-alert">
    <CmkAlert variant="warning" :heading="_t('Filters left out')" :text="untranslated(warning)" />
  </div>
</template>

<style scoped>
.db-dropped-filters-alert {
  padding-left: var(--dimension-4);
  padding-right: var(--dimension-4);
}
</style>
