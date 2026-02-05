<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon'

interface Props {
  filterName: string
}

defineProps<Props>()

const emit = defineEmits<{
  remove: []
}>()

const { _t } = usei18n()
</script>

<template>
  <button
    class="db-remove-filter-button"
    :aria-label="_t('Remove %{name} filter', { name: filterName })"
    @click="emit('remove')"
  >
    <CmkIcon :aria-label="_t('Remove filter')" name="close" size="xxsmall" />
  </button>
</template>

<style scoped>
.db-remove-filter-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--dimension-6);
  height: var(--dimension-6);
  margin: 0;
  padding: 0;
  background: none;
  border: none;
  color: var(--font-color-breadcrumb-inactive);
  cursor: pointer;
  font-size: var(--font-size-large);
  font-weight: bold;
}
</style>
