<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

const { _t } = usei18n()

const props = defineProps<{ openedCount: number; totalCount: number }>()

const emit = defineEmits<{
  'expand-all': []
  'collapse-all': []
}>()

const options = computed(() => [
  { label: _t('Collapse all'), value: 'collapse' },
  { label: _t('Expand all'), value: 'expand' }
])

const selected = computed<string | null>(() => {
  if (props.openedCount === 0) {
    return 'expand'
  }
  if (props.openedCount === props.totalCount) {
    return 'collapse'
  }
  return null
})

function onSelect(value: string): void {
  switch (value) {
    case 'expand':
      emit('expand-all')
      break
    case 'collapse':
      emit('collapse-all')
      break
  }
}
</script>

<template>
  <CmkToggleButtonGroup
    :options="options"
    :model-value="selected"
    spacing="none"
    @update:model-value="onSelect"
  />
</template>
