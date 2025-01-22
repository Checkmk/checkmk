<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { computed } from 'vue'
import { Label } from 'radix-vue'

const labelVariants = cva('', {
  variants: {
    variant: {
      default: '',
      title: 'cmk-label--title',
      subtitle: 'cmk-label--subtitle'
    }
  },
  defaultVariants: {
    variant: 'default'
  }
})
type LabelVariants = VariantProps<typeof labelVariants>

interface LabelProps {
  variant?: LabelVariants['variant']
  onClick?: (() => void) | null
}

const props = defineProps<LabelProps>()

const delegatedProps = computed(() => {
  const { variant: _, ...delegated } = props

  return delegated
})

const onClickCallback = props.onClick ? props.onClick : undefined
</script>

<template>
  <Label
    v-bind="delegatedProps"
    :class="[labelVariants({ variant }), { 'cmk-label--clickable': !!props.onClick }]"
    @click="onClickCallback"
  >
    <slot />
  </Label>
</template>

<style scoped>
label {
  display: block;

  &.cmk-label--title {
    height: 24px;
    align-content: center;
    font-weight: var(--font-weight-bold);
    font-size: var(--font-size-xlarge);
  }

  &.cmk-label--subtitle {
    font-size: var(--font-size-normal);
    margin-bottom: var(--spacing);
  }

  &.cmk-label--clickable {
    cursor: pointer;
    pointer-events: all;
  }
}
</style>
