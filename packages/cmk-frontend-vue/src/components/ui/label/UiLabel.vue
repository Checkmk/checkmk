<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { computed } from 'vue'
import { Label, type LabelProps } from 'radix-vue'

const labelVariants = cva('', {
  variants: {
    variant: {
      default: '',
      title: 'label_title',
      subtitle: 'label_subtitle'
    }
  },
  defaultVariants: {
    variant: 'default'
  }
})
type LabelVariants = VariantProps<typeof labelVariants>

const props = defineProps<
  LabelProps & {
    variant?: LabelVariants['variant']
  }
>()

const delegatedProps = computed(() => {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { variant: _, ...delegated } = props

  return delegated
})
</script>

<template>
  <Label v-bind="delegatedProps" :class="labelVariants({ variant })">
    <slot />
  </Label>
</template>

<style scoped>
.label_title {
  font-weight: bold;
  font-size: large;
  position: relative;
  top: -0.2rem;
}

.label_subtitle {
  font-weight: normal;
  font-size: small;
  position: relative;
}
</style>
