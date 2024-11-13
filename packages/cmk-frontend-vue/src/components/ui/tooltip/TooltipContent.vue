<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type HTMLAttributes, computed } from 'vue'
import {
  TooltipContent,
  type TooltipContentEmits,
  type TooltipContentProps,
  TooltipPortal,
  useForwardPropsEmits
} from 'radix-vue'

defineOptions({
  inheritAttrs: false
})

const props = withDefaults(
  defineProps<TooltipContentProps & { class?: HTMLAttributes['class'] }>(),
  {
    sideOffset: 4,
    class: ''
  }
)

const emits = defineEmits<TooltipContentEmits>()

const delegatedProps = computed(() => {
  const delegated = { ...props }
  delete delegated.class

  return delegated
})

const forwarded = useForwardPropsEmits(delegatedProps, emits)
</script>

<template>
  <TooltipPortal>
    <!-- @vue-expect-error Radix-vue props doesn't follow our exactOptionalPropertyTypes rule -->
    <TooltipContent v-bind="{ ...forwarded, ...$attrs }" :class="props.class">
      <slot />
    </TooltipContent>
  </TooltipPortal>
</template>
