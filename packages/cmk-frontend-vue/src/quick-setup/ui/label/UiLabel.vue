<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { computed } from 'vue'
import { Label, type LabelProps } from 'radix-vue'

const labelVariants = cva('', {
  variants: {
    variant: {
      default: '',
      title: 'qs-ui-label--title',
      subtitle: 'qs-ui-label--subtitle'
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
  <!-- @vue-expect-error Radix-vue props doesn't follow our exactOptionalPropertyTypes rule -->
  <Label v-bind="delegatedProps" :class="labelVariants({ variant })">
    <slot />
  </Label>
</template>

<style scoped>
label {
  display: block;

  &.qs-ui-label--title {
    height: 24px;
    align-content: center;
    font-weight: var(--font-weight-bold);
    font-size: var(--font-size-xlarge);
  }

  &.qs-ui-label--subtitle {
    font-size: var(--font-size-normal);
    margin-bottom: var(--spacing);
  }
}
</style>
