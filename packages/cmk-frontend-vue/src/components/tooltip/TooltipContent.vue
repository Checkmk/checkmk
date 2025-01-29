<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type HTMLAttributes, computed } from 'vue'
import { TooltipContent, TooltipPortal, useForwardPropsEmits } from 'radix-vue'

defineOptions({
  inheritAttrs: false
})

type TooltipContentEmits = {
  escapeKeyDown: [event: KeyboardEvent]
  pointerDownOutside: [event: Event]
}

const emits = defineEmits<TooltipContentEmits>()

interface TooltipContentProps {
  asChild?: boolean
  sideOffset?: number
  side?: 'right' | 'left' | 'top' | 'bottom'
  align?: 'center' | 'end' | 'start'
  class?: string
}

const props = withDefaults(
  defineProps<TooltipContentProps & { class?: HTMLAttributes['class'] }>(),
  {
    sideOffset: 4,
    class: '',
    side: 'top',
    align: 'center'
  }
)

const delegatedProps = computed(() => {
  const delegated = { ...props }
  delete delegated.class

  return delegated
})

const forwarded = useForwardPropsEmits(delegatedProps, emits)
</script>

<template>
  <TooltipPortal>
    <TooltipContent v-bind="{ ...forwarded, ...$attrs }" :class="props.class">
      <slot />
    </TooltipContent>
  </TooltipPortal>
</template>
