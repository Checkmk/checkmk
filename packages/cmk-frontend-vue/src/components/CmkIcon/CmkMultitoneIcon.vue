<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup generic="IconName extends CmkMultitoneIconNames" lang="ts">
import { computed, ref } from 'vue'

import { immediateWatch } from '@/lib/watch'

import { cmkMultitoneIconVariants, oneColorIcons, twoColorIcons } from './icons.constants.ts'
import type {
  CmkMultitoneIconColor,
  CmkMultitoneIconNames,
  CustomIconColor,
  IconSizeNames,
  OneColorIcons,
  TwoColorIcons
} from './types.ts'
import { iconSizeNametoNumber } from './utils'

const props = defineProps<{
  name: IconName
  primaryColor: CmkMultitoneIconColor | CustomIconColor
  secondaryColor?: IconName extends OneColorIcons ? never : CmkMultitoneIconColor | CustomIconColor
  size?: IconSizeNames | undefined
  title?: string | undefined
  rotate?: number | undefined
}>()
function getTransformRotate(): string {
  return `rotate(${props.rotate || 0}deg)`
}

const iconSize = computed(() => iconSizeNametoNumber(props.size))

function getCustomColor(color: CmkMultitoneIconColor | CustomIconColor): string {
  if (!color) {
    return 'unset'
  }
  if (typeof color === 'object' && 'custom' in color) {
    return color.custom
  }
  return 'unset'
}
const customColorPrimary = computed(() => getCustomColor(props.primaryColor))
const customColorSecondary = computed(() => getCustomColor(props.secondaryColor ?? null))

function getColorClass(color: CmkMultitoneIconColor | CustomIconColor, prefix: string): string {
  if (!color) {
    return ''
  }
  if (typeof color === 'object' && 'custom' in color) {
    return `${prefix}-custom`
  }
  return `${prefix}-${cmkMultitoneIconVariants({ color: color || null })}`
}

function getColorClasses(name: OneColorIcons | TwoColorIcons): string[] {
  if (oneColorIcons.includes(name as OneColorIcons)) {
    return [getColorClass(props.primaryColor, 'color')].filter(Boolean)
  }
  if (twoColorIcons.includes(name as TwoColorIcons)) {
    return [
      getColorClass(props.primaryColor, 'color'),
      'secondaryColor' in props &&
        props.secondaryColor &&
        getColorClass(props.secondaryColor, 'color-secondary')
    ].filter(Boolean) as string[]
  }
  return []
}
function getIconFileName(iconName: CmkMultitoneIconNames): string {
  return `icon-${iconName}`
}
const svg = ref<string | null>(null)

async function loadSvg() {
  svg.value = (await import(`@/assets/icons/${getIconFileName(props.name)}.svg?raw`)).default
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
    :class="getColorClasses(props.name)"
    :title="props.title || getIconFileName(props.name)"
    v-html="svg"
  ></div>
</template>

<style>
/* stylelint-disable checkmk/vue-bem-naming-convention */
.cmk-multitone-icon {
  margin: 0;
  padding: 0;
  vertical-align: baseline;
  width: v-bind('`${iconSize}px`');
  height: v-bind('`${iconSize}px`');
  transform: v-bind('getTransformRotate()');

  --icon-primary-color: var(--color-corporate-green-60);
  --icon-secondary-color: var(--color-corporate-green-60);
  --icon-tertiary-color: var(--color-corporate-green-60);

  svg {
    width: 100%;
    height: 100%;
  }

  /* Primary icon colors */
  &.color-green {
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

  &.color-font {
    --icon-primary-color: var(--font-color);
  }

  &.color-custom {
    --icon-primary-color: v-bind(customColorPrimary);
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

  &.color-secondary-font {
    --icon-secondary-color: var(--font-color);
  }

  &.color-secondary-custom {
    --icon-secondary-color: v-bind(customColorSecondary);
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

  &.color-tertiary-font {
    --icon-tertiary-color: var(--font-color);
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

svg .icon-primary-color-stroke {
  stroke: var(--icon-primary-color);
}

svg .icon-secondary-color-stroke {
  stroke: var(--icon-secondary-color);
}

svg .icon-tertiary-color-stroke {
  stroke: var(--icon-tertiary-color);
}
</style>
