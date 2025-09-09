<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { ref } from 'vue'

import { immediateWatch } from '@/lib/watch'

const cmkIconVariants = cva('', {
  variants: {
    name: {
      aggr: 'icon-aggr',
      services: 'icon-services'
    },
    color: {
      success: 'green',
      hosts: 'blue',
      info: 'blue',
      warning: 'yellow',
      services: 'yellow',
      danger: 'red',
      customization: 'pink',
      others: 'grey',
      users: 'purple',
      specialAgents: 'cyan'
    },
    size: {
      xsmall: '10px',
      small: '12px',
      medium: '15px',
      large: '18px',
      xlarge: '20px',
      xxlarge: '32px',
      xxxlarge: '77px'
    }
  },
  defaultVariants: {
    size: 'medium'
  }
})

export type CmkIconSize = VariantProps<typeof cmkIconVariants>['size']
export type CmkMultitoneIconName = VariantProps<typeof cmkIconVariants>['name']
export type CmkMultitoneIconColor = VariantProps<typeof cmkIconVariants>['color']

const props = defineProps<CmkMultitoneIconProps>()

function getTransformRotate(): string {
  return `rotate(${props.rotate || 0}deg)`
}

function getSize(): string {
  return cmkIconVariants({ color: null, size: props.size, name: null })
}

function getColorClass(color: CmkMultitoneIconColor, prefix: string): string {
  if (!color) {
    return ''
  }
  return `${prefix}-${cmkIconVariants({ color: color || null, size: null, name: null })}`
}

function getColorClasses(): string[] {
  return [
    getColorClass(props.primaryColor, 'color'),
    getColorClass(props.secondaryColor, 'color-secondary'),
    getColorClass(props.tertiaryColor, 'color-tertiary')
  ].filter((c) => c !== '')
}

interface CmkMultitoneIconProps {
  name: CmkMultitoneIconName
  size?: CmkIconSize
  primaryColor: CmkMultitoneIconColor
  secondaryColor?: CmkMultitoneIconColor
  tertiaryColor?: CmkMultitoneIconColor
  title?: string | undefined
  rotate?: number | undefined
}

const svg = ref<string | null>(null)

async function loadSvg() {
  svg.value = (
    await import(
      `@/assets/icons/${cmkIconVariants({ name: props.name, size: null, color: null })}.svg?raw`
    )
  ).default
}

immediateWatch(
  () => ({ newName: props.name }),
  async () => {
    await loadSvg()
  }
)
</script>

<template>
  <!-- eslint-disable vue/no-v-html -->
  <div
    v-if="svg"
    class="cmk-multitone-icon"
    :class="getColorClasses()"
    :title="props.title || cmkIconVariants({ name: props.name, size: null, color: null })"
    v-html="svg"
  ></div>
</template>

<style>
/* stylelint-disable checkmk/vue-bem-naming-convention */
.cmk-multitone-icon {
  margin: 0;
  padding: 0;
  vertical-align: baseline;
  width: v-bind('getSize()');
  height: v-bind('getSize()');
  transform: v-bind('getTransformRotate()');

  --icon-primary-color: var(--color-corporate-green-60);
  --icon-secondary-color: var(--color-corporate-green-60);
  --icon-tertiary-color: var(--color-corporate-green-60);

  svg {
    width: 100%;
    height: 100%;
  }

  /* Primary icon colors */
  &.primary-color-green {
    --icon-primary-color: var(--color-corporate-green-60);
  }

  &.color-blue {
    --icon-primary-color: var(--color-light-blue-60);
  }

  &.color-yellow {
    --icon-primary-color: var(--color-yellow-60);
  }

  &.color-red {
    --icon-primary-color: var(--color-light-red-60);
  }

  &.color-orange {
    --icon-primary-color: var(--color-orange-60);
  }

  &.color-pink {
    --icon-primary-color: var(--color-pink-60);
  }

  &.color-grey {
    --icon-primary-color: var(--color-mist-grey-60);
  }

  &.color-purple {
    --icon-primary-color: var(--color-purple-60);
  }

  &.color-cyan {
    --icon-primary-color: var(--color-cyan-60);
  }

  &.color-brown {
    --icon-primary-color: var(--color-brown-60);
  }

  /* Secondary icon colors */
  &.color-secondary-green {
    --icon-secondary-color: var(--color-corporate-green-60);
  }

  &.color-secondary-blue {
    --icon-secondary-color: var(--color-light-blue-60);
  }

  &.color-secondary-yellow {
    --icon-secondary-color: var(--color-yellow-60);
  }

  &.color-secondary-red {
    --icon-secondary-color: var(--color-light-red-60);
  }

  &.color-secondary-orange {
    --icon-secondary-color: var(--color-orange-60);
  }

  &.color-secondary-pink {
    --icon-secondary-color: var(--color-pink-60);
  }

  &.color-secondary-grey {
    --icon-secondary-color: var(--color-mist-grey-60);
  }

  &.color-secondary-purple {
    --icon-secondary-color: var(--color-purple-60);
  }

  &.color-secondary-cyan {
    --icon-secondary-color: var(--color-cyan-60);
  }

  &.color-secondary-brown {
    --icon-secondary-color: var(--color-brown-60);
  }

  /* Secondary icon colors */
  &.color-tertiary-green {
    --icon-tertiary-color: var(--color-corporate-green-60);
  }

  &.color-tertiary-blue {
    --icon-tertiary-color: var(--color-light-blue-60);
  }

  &.color-tertiary-yellow {
    --icon-tertiary-color: var(--color-yellow-60);
  }

  &.color-tertiary-red {
    --icon-tertiary-color: var(--color-light-red-60);
  }

  &.color-tertiary-orange {
    --icon-tertiary-color: var(--color-orange-60);
  }

  &.color-tertiary-pink {
    --icon-tertiary-color: var(--color-pink-60);
  }

  &.color-tertiary-grey {
    --icon-tertiary-color: var(--color-mist-grey-60);
  }

  &.color-tertiary-purple {
    --icon-tertiary-color: var(--color-purple-60);
  }

  &.color-tertiary-cyan {
    --icon-tertiary-color: var(--color-cyan-60);
  }

  &.color-tertiary-brown {
    --icon-tertiary-color: var(--color-brown-60);
  }
}

/* Set svg multitone fill */
svg .icon-primary-color {
  fill: var(--icon-primary-color);
}

svg .icon-secondary-color {
  fill: var(--icon-secondary-color);
}

svg .icon-tertiary-color {
  fill: var(--icon-tertiary-color);
}
</style>
