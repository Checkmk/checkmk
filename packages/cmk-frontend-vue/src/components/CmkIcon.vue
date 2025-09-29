<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'

function getIconVariable(iconName: string | undefined): string {
  /*
    Transforms a kebab-case icon name to a CSS variable reference.
    E.g. "main-help" -> "var(--icon-main-help)"
  */
  if (!iconName) {
    return 'none'
  }

  const errors: string[] = []
  if (iconName.includes('_')) {
    errors.push(
      `Icon name "${iconName}" contains an underscore (_). Use kebab-case (dashes) instead.`
    )
  }
  if (iconName.startsWith('icon')) {
    errors.push(
      `Icon name "${iconName}" contains "icon". Pass only the base name, e.g. "main-help".`
    )
  }
  if (iconName.includes('.svg')) {
    errors.push(`Icon name "${iconName}" contains ".svg". Do not include file extensions.`)
  }

  if (errors.length > 0) {
    throw new Error(errors.join(' '))
  }

  const iconVar = `icon-${iconName}`

  return `var(--${iconVar})`
}

const cmkIconVariants = cva('', {
  variants: {
    variant: {
      plain: '',
      inline: 'cmk-icon--inline'
    },
    size: {
      xxsmall: '8px',
      xsmall: '10px',
      small: '12px',
      medium: '15px',
      large: '18px',
      xlarge: '20px',
      xxlarge: '32px',
      xxxlarge: '77px'
    },
    colored: {
      true: '',
      false: 'cmk-icon--colorless'
    }
  },
  defaultVariants: {
    variant: 'plain',
    size: 'medium',
    colored: true
  }
})
export type CmkIconVariants = VariantProps<typeof cmkIconVariants>

export interface CmkIconProps {
  /** @property {string} name - Name of the icon */
  name: string

  /** @property {undefined | CmkIconVariants['variant']} variant - Styling variant of the icon */
  variant?: CmkIconVariants['variant'] | undefined

  /** @property {undefined | CmkIconVariants['size']} size - Width and height of the icon */
  size?: CmkIconVariants['size'] | undefined

  /** @property {undefined | CmkIconVariants['colored']} colored - Whether the icon is colored or black and white */
  colored?: CmkIconVariants['colored'] | undefined

  /** @property {undefined | number} rotate - Transform rotate value in degrees */
  rotate?: number | undefined

  /** @property {undefined | string} title - Title to be displayed on hover */
  title?: string | undefined
}

const props = defineProps<CmkIconProps>()

const getTransformRotate = () => {
  return `rotate(${props.rotate || 0}deg)`
}
</script>

<template>
  <img
    class="cmk-icon"
    :class="cmkIconVariants({ variant: props.variant, size: null, colored: props.colored })"
    :title="title || ''"
    :alt="title || ''"
  />
</template>

<style scoped>
.cmk-icon {
  margin: 0;
  padding: 0;
  vertical-align: baseline;
  content: v-bind('getIconVariable(name)');
  width: v-bind('cmkIconVariants({size})') !important;
  height: v-bind('cmkIconVariants({size})') !important;
  transform: v-bind('getTransformRotate()');

  &.cmk-icon--inline {
    display: inline-block;
    margin-right: var(--spacing-half);
    vertical-align: middle;
  }

  &.cmk-icon--colorless {
    filter: grayscale(100%);
  }
}
</style>
