<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { cva, type VariantProps } from 'class-variance-authority'

const propsCva = cva('', {
  variants: {
    size: {
      small: 'cmk-keyboard-key-size-small',
      medium: 'cmk-keyboard-key-size-medium',
      large: 'cmk-keyboard-key-size-large'
    }
  },
  defaultVariants: {
    size: 'medium'
  }
})

type KeyboardKey =
  | 'arrow-left'
  | 'arrow-right'
  | 'arrow-up'
  | 'arrow-down'
  | 'enter'
  | 'backspace'
  | string

export type Sizes = VariantProps<typeof propsCva>['size']

export interface CmkKeyboardKeyProps {
  keyboardKey: KeyboardKey
  size?: Sizes
}

const props = defineProps<CmkKeyboardKeyProps>()

function isKeySymbol(): boolean {
  switch (props.keyboardKey) {
    case 'arrow-left':
    case 'arrow-right':
    case 'arrow-up':
    case 'arrow-down':
    case 'enter':
    case 'backspace':
      return true
    default:
      return false
  }
}

function getKeyContent(): string {
  if (!isKeySymbol()) {
    return props.keyboardKey
  }
  switch (props.keyboardKey) {
    case 'arrow-left':
      return '←'
    case 'arrow-right':
      return '→'
    case 'arrow-up':
      return '↑'
    case 'arrow-down':
      return '↓'
    case 'enter':
      return '↵'
    case 'backspace':
      return '⇽'
    default:
      return props.keyboardKey
  }
}

function getKeyClass(): string {
  if (isKeySymbol()) {
    return `unicode ${props.keyboardKey} ${propsCva({ size: props.size })}`
  }
  return propsCva({ size: props.size })
}
</script>

<template>
  <span class="cmk-keyboard-key" :class="getKeyClass()">
    <span>{{ getKeyContent() }}</span>
  </span>
</template>

<style scoped>
.cmk-keyboard-key {
  border-radius: 4px;
  text-align: center;
  margin: 0 4px;
  background: var(--color-midnight-grey-40, var(--font-color));
  border: 1px solid var(--color-midnight-grey-40, var(--font-color));
  color: var(--white);
  display: inline-flex;
  justify-content: center;
  span {
    margin: 1px 0;
  }
}

.cmk-keyboard-key-size-small {
  font-size: 10px;
  line-height: 10px;
  padding: 1px 3px;
  min-width: 8px;
}

.cmk-keyboard-key-size-medium {
  font-size: 12px;
  line-height: 12px;
  padding: 2px 4px;
  min-width: 10px;
}

.cmk-keyboard-key-size-large {
  font-size: 14px;
  line-height: 14px;
  padding: 4px 5px;
  min-width: 12px;
}

.unicode {
  overflow: hidden;
  position: relative;

  span {
    position: relative;
    margin: 0 0 2px 0;
  }

  &.cmk-keyboard-key-size-small {
    font-size: 16px;
    top: 1px;
  }

  &.cmk-keyboard-key-size-medium {
    font-size: 20px;
    top: 2px;
  }

  &.cmk-keyboard-key-size-large {
    font-size: 24px;
    top: 3px;
  }

  &.arrow-left,
  &.arrow-right {
    padding-left: 0;
    padding-right: 0;
  }

  &.enter {
    span {
      top: 2px;
    }
  }

  &.backspace {
    padding-left: 2px;
    padding-right: 2px;

    span {
      top: 1px;
    }
  }
}
</style>
