<script setup lang="ts">
import ToolTip from '@/quick-setup/components/ToolTip.vue'

import { type TextWidgetProps } from './widget_types'

defineProps<TextWidgetProps>()
</script>

<template>
  <span
    >{{ text }}
    <ToolTip v-if="tooltip"
      ><p>{{ tooltip }}</p></ToolTip
    ></span
  >
</template>

<style scoped></style>
