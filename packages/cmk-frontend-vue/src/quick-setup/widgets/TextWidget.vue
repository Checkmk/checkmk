<script setup lang="ts">
import ToolTip from '@/quick-setup/components/ToolTip.vue'

import { type TextWidgetProps } from './widget_types'

defineProps<TextWidgetProps>()
</script>

<template>
  <span class="qs-text-widget"
    >{{ text }}
    <ToolTip v-if="tooltip"
      ><p>{{ tooltip }}</p></ToolTip
    ></span
  >
</template>

<style scoped>
.qs-text-widget {
  margin-bottom: var(--spacing);
}
</style>
