<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

const { _t } = usei18n()

const props = withDefaults(defineProps<{ total?: number }>(), { total: 0 })

const label = computed(() => _t('Total rows: %{total}', { total: props.total }))
</script>

<template>
  <p v-if="total > 0" class="monitoring-total-count">{{ label }}</p>
</template>

<style scoped>
.monitoring-total-count {
  margin: 0;
  white-space: nowrap;
}
</style>
