<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import CmkButton from '@/components/CmkButton.vue'

interface WidgetItemProps {
  enabled: boolean
  selected: boolean
  name: string
}

const props = defineProps<WidgetItemProps>()
const emit = defineEmits<{
  update: [widgetName: string]
}>()

const updateSelelection = () => {
  if (props.enabled) {
    emit('update', props.name)
  }
}

const itemVariant = computed(() => {
  if (!props.enabled) {
    return 'danger'
  }

  if (props.selected) {
    return 'primary'
  }
  return 'secondary'
})
</script>

<template>
  <div class="widget-item">
    <CmkButton :variant="itemVariant" @click="updateSelelection">{{ name }}</CmkButton>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.widget-item {
  flex: 1;
}
</style>
