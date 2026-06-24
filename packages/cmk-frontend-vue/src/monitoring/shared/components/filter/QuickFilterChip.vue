<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkChip, { type Colors, type Variants } from '@/components/CmkChip.vue'

const props = defineProps<{
  label: string
  active: boolean
}>()

const emit = defineEmits<{
  activate: []
  deactivate: []
}>()

function getColor(): Colors {
  return props.active ? 'success' : 'others'
}

function getVariant(): Variants {
  return props.active ? 'fill' : 'outline'
}

function toggle(): void {
  if (props.active) {
    emit('deactivate')
  } else {
    emit('activate')
  }
}
</script>

<template>
  <CmkChip
    type="button"
    :aria-pressed="active"
    :color="getColor()"
    :variant="getVariant()"
    @click="toggle"
  >
    {{ label }}
  </CmkChip>
</template>
