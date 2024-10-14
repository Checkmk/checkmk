<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { getIconVariable } from '@/lib/utils'

const cmkIconVariants = cva('', {
  variants: {
    variant: {
      plain: '',
      inline: 'icon-element--inline'
    },
    size: {
      xsmall: '10px',
      small: '12px',
      medium: '15px',
      large: '18px',
      xlarge: '20px',
      xxlarge: '32px'
    }
  },
  defaultVariants: {
    variant: 'plain',
    size: 'medium'
  }
})
export type CmkIconVariants = VariantProps<typeof cmkIconVariants>

interface CmkIconProps {
  /** @property {string} name - Name of the icon */
  name: string

  /** @property {undefined | CmkIconVariants['variant']} variant - Styling variant of the icon */
  variant?: CmkIconVariants['variant']

  /** @property {undefined | CmkIconVariants['size']} size - Width and height of the icon */
  size?: CmkIconVariants['size']

  /** @property {undefined | number} rotate - Transform rotate value in degrees */
  rotate?: number

  /** @property {undefined | string} title - Title to be displayed on hover */
  title?: string
}

const props = defineProps<CmkIconProps>()

const getTransformRotate = () => {
  return `rotate(${props.rotate || 0}deg)`
}
</script>

<template>
  <img
    class="icon-element"
    :class="cmkIconVariants({ variant: props.variant, size: null })"
    :title="title || ''"
    :alt="title || ''"
  />
</template>

<style scoped>
.icon-element {
  margin: 0;
  padding: 0;
  vertical-align: baseline;

  content: v-bind(getIconVariable(name));
  width: v-bind(cmkIconVariants({size}));
  height: v-bind(cmkIconVariants({size}));
  transform: v-bind(getTransformRotate());

  &.icon-element--inline {
    margin-right: var(--spacing-half);
    vertical-align: middle;
  }
}
</style>
