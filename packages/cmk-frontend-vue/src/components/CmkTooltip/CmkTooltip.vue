<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { TooltipRoot } from 'radix-vue'

type TooltipEmits = {
  'update:open': [value: boolean]
}
interface TooltipProps {
  open: boolean
  disableClosingTrigger?: boolean
}

defineProps<TooltipProps>()
const emit = defineEmits<TooltipEmits>()
</script>

<template>
  <TooltipRoot
    :open="open"
    :disable-closing-trigger="disableClosingTrigger ?? false"
    @update:open="emit('update:open', $event)"
  >
    <slot />
  </TooltipRoot>
</template>
