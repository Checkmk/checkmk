<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { Primitive, type PrimitiveProps } from 'radix-vue'

interface Props extends PrimitiveProps {
  class?: HTMLAttributes['class']
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  size: 'default',
  class: '',
  as: 'button'
})
</script>

<template>
  <Primitive :as="as" :as-child="asChild" :class="props.class">
    <slot />
  </Primitive>
</template>
