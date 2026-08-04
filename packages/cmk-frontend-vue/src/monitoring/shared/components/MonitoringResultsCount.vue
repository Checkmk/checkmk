<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

const { _t } = usei18n()

const props = withDefaults(
  defineProps<{
    matched?: number
    narrowed?: boolean
  }>(),
  { matched: 0, narrowed: false }
)

const visible = computed(() => props.narrowed && props.matched > 0)

const label = computed(() => _t('Rows matching your criteria: %{count}', { count: props.matched }))
</script>

<template>
  <p class="monitoring-results-count" aria-live="polite">{{ visible ? label : '' }}</p>
</template>

<style scoped>
.monitoring-results-count {
  min-height: 1lh;
  margin: 0;
}
</style>
