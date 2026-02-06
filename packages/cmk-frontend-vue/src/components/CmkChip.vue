<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'

const propsCva = cva('', {
  variants: {
    size: {
      small: 'cmk-chip--size-small',
      medium: 'cmk-chip--size-medium',
      large: 'cmk-chip--size-large'
    },
    color: {
      success: 'cmk-chip--color-green',
      hosts: 'cmk-chip--color-blue',
      info: 'cmk-chip--color-blue',
      warning: 'cmk-chip--color-yellow',
      services: 'cmk-chip--color-yellow',
      danger: 'cmk-chip--color-red',
      customization: 'cmk-chip--color-pink',
      others: 'cmk-chip--color-grey',
      users: 'cmk-chip--color-purple',
      specialAgents: 'cmk-chip--color-cyan'
    },
    variant: {
      fill: 'cmk-chip--variant-fill',
      outline: 'cmk-chip--variant-outline'
    }
  },
  defaultVariants: {
    size: 'medium',
    color: 'success',
    variant: 'fill'
  }
})

export type Sizes = VariantProps<typeof propsCva>['size']
export type Colors = VariantProps<typeof propsCva>['color']
export type Variants = VariantProps<typeof propsCva>['variant']

export interface CmkChipProps {
  size?: Sizes
  color?: Colors
  variant?: Variants
  asDiv?: boolean | undefined
  disabled?: boolean | undefined
}

defineProps<CmkChipProps>()
</script>

<template>
  <component
    :is="asDiv ? 'div' : 'button'"
    class="cmk-chip"
    :class="propsCva({ size, color, variant })"
    :disabled="disabled"
  >
    <div class="cmk-chip__content">
      <div class="cmk-chip__state-indicator"></div>
      <slot name="start" />
      <span><slot /></span>
      <slot name="end" />
    </div>
  </component>
</template>

<style scoped>
.cmk-chip {
  border-radius: 4px;
  text-align: center;
  font-weight: var(--font-weight-default);
  position: relative;
  padding: 0;
  margin: 0;
  border: 1px solid transparent;
  background: transparent;
  width: auto;
  display: flex;

  --chip-color: var(--color-corporate-green-50);
  --chip-fill-hover-color: var(--white);
  --chip-fill-hover-opacity: 0.3;
  --chip-fill-font-color: var(--black);
  --chip-fill-active-color: var(--conference-grey-10);
  --chip-fill-active-opacity: 0.1;
  --chip-outline-hover-color: var(--ux-theme-5);
  --chip-outline-hover-opacity: 1;
  --chip-outline-active-opacity: 1;

  &.cmk-chip--color-green {
    --chip-color: var(--color-corporate-green-50);
  }

  &.cmk-chip--color-blue {
    --chip-color: var(--color-light-blue-50);
  }

  &.cmk-chip--color-yellow {
    --chip-color: var(--color-yellow-50);
    --chip-outline-font-color: var(--chip-outline-yellow-font-color, var(--color-yellow-50));
  }

  &.cmk-chip--color-red {
    --chip-color: var(--color-light-red-60);
    --chip-fill-font-color: var(--white);
  }

  &.cmk-chip--color-pink {
    --chip-color: var(--color-pink-50);
  }

  &.cmk-chip--color-grey {
    --chip-color: var(--color-mid-grey-50);
    --chip-outline-font-color: var(--font-color);
  }

  &.cmk-chip--color-purple {
    --chip-color: var(--color-purple-50);
  }

  &.cmk-chip--color-cyan {
    --chip-color: var(--color-cyan-50);
  }

  &.cmk-chip--color-brown {
    --chip-color: var(--color-brown-50);
    --chip-fill-font-color: var(--white);
  }

  .cmk-chip__state-indicator {
    border-radius: 9999px;
    position: absolute;
    background: transparent;
    inset: 0;
    border: 1px solid transparent;
  }

  .cmk-chip__content {
    overflow: hidden;
    border-radius: 9999px;
    position: relative;
    background: transparent;
    inset: 0;
    display: flex;
    flex-direction: row;
    align-items: center;

    *:not(.cmk-chip__state-indicator) {
      z-index: +1;
    }
  }

  &.cmk-chip--size-small {
    .cmk-chip__content {
      font-size: 10px;
      padding: var(--dimension-1) var(--dimension-3);
      gap: var(--dimension-2);
    }
  }

  &.cmk-chip--size-medium {
    .cmk-chip__content {
      font-size: 12px;
      padding: var(--dimension-2) var(--dimension-4);
      gap: var(--dimension-3);
    }
  }

  &.cmk-chip--size-large {
    .cmk-chip__content {
      font-size: 14px;
      padding: 3px var(--dimension-4);
      gap: 6px;
    }
  }

  &.cmk-chip--variant-fill {
    .cmk-chip__content {
      background-color: var(--chip-color);
      border: 1px solid var(--chip-color);
      color: var(--chip-fill-font-color);
    }
  }

  &.cmk-chip--variant-outline {
    .cmk-chip__content {
      background-color: var(--ux-theme-0);
      border: 1px solid var(--chip-color);
      color: var(--chip-outline-font-color, var(--chip-color));
    }
  }

  &:is(button) {
    &:hover {
      &.cmk-chip--variant-outline {
        .cmk-chip__state-indicator {
          opacity: var(--chip-outline-hover-opacity);
          background-color: var(--chip-outline-hover-color);
        }
      }

      &.cmk-chip--variant-fill {
        .cmk-chip__state-indicator {
          opacity: var(--chip-fill-hover-opacity);
          background-color: var(--chip-fill-hover-color);
        }
      }
    }

    &:active {
      border-radius: 99999px;

      &.cmk-chip--variant-outline {
        .cmk-chip__state-indicator {
          opacity: var(--chip-outline-active-opacity);
          background-color: var(--chip-outline-active-color);
        }
      }

      &.cmk-chip--variant-fill {
        .cmk-chip__state-indicator {
          opacity: var(--chip-fill-active-opacity);
          background-color: var(--chip-fill-active-color);
        }
      }
    }

    &:disabled {
      border-radius: 9999px;
      opacity: 0.5;
      filter: none;

      &.cmk-chip--variant-outline,
      &.cmk-chip--variant-fill {
        .cmk-chip__state-indicator {
          opacity: 1;
          background: inherit;
        }
      }
    }

    &:focus-visible {
      border: 1px solid var(--success);
    }
  }
}

body[data-theme='facelift'] .cmk-chip {
  --chip-outline-active-color: var(--ux-theme-5);
  --chip-outline-yellow-font-color: var(--font-color);
}
</style>
