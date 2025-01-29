<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { TooltipRoot, useForwardPropsEmits } from 'radix-vue'

type TooltipEmits = {
  'update:open': [value: boolean]
}
interface TooltipProps {
  open?: boolean
  disableClosingTrigger?: boolean
}

const props = defineProps<TooltipProps>()
const emits = defineEmits<TooltipEmits>()

const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <TooltipRoot v-bind="forwarded">
    <slot />
  </TooltipRoot>
</template>
