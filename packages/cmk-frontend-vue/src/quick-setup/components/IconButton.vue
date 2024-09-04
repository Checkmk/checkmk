<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'

import { getIconVariable } from '@/lib/utils'
import { Button } from '@/quick-setup/ui/button'

const buttonVariants = cva('', {
  variants: {
    variant: {
      custom: 'qs-icon-button--custom',
      next: 'qs-icon-button--next',
      prev: 'qs-icon-button--prev',
      save: 'qs-icon-button--save'
    }
  },
  defaultVariants: {
    variant: 'custom'
  }
})
type ButtonVariants = VariantProps<typeof buttonVariants>

interface IconButtonProps {
  /** @property {string} label - Button's caption */
  label: string

  /** @property {ButtonVariants['variant']} variant - Type of button */
  variant?: ButtonVariants['variant']

  /** @property {string} ariaLabel - Aria label for the button */
  ariaLabel?: string

  /** @property {string} iconName - Name of the icon to be displayed inside the button
      used for custom icon buttons only */
  iconName?: string
}

const props = defineProps<IconButtonProps>()
defineEmits(['click'])

let selectedAriaLabel = ''

if (props?.variant) {
  switch (props.variant) {
    case 'custom':
      selectedAriaLabel = props.ariaLabel || ''
      break
    case 'prev':
      selectedAriaLabel = 'Go to the previous stage'
      break
    case 'next':
      selectedAriaLabel = 'Go to the next stage'
      break
    case 'save':
      selectedAriaLabel = 'Save'
      break
  }
}
</script>

<template>
  <Button
    class="qs-icon-button button"
    :class="buttonVariants({ variant })"
    :aria-label="selectedAriaLabel"
    @click="$emit('click')"
  >
    <div class="icon" />
    <span>{{ props.label }}</span>
  </Button>
</template>

<style scoped>
.qs-icon-button {
  padding: 7px 8px 6px;

  &:first-child {
    margin: 0;
  }

  div.icon {
    display: inline-block;
    background-size: 15px;
    width: 15px;
    height: 15px;
    margin-right: var(--spacing-half);
  }

  span {
    position: relative;
    top: 1px;
  }
}

.qs-icon-button--next,
.qs-icon-button--save {
  border: 1px solid var(--default-submit-button-border-color);
}

.qs-icon-button--next div.icon {
  background-image: var(--icon-continue);
  transform: rotate(90deg);
}

.qs-icon-button--save div.icon {
  background-image: var(--icon-save-to-services);
}

.qs-icon-button--prev div.icon {
  background-image: var(--icon-back);
  transform: rotate(90deg);
}

.qs-icon-button--custom div.icon {
  background-image: v-bind('getIconVariable(props?.iconName)');
}
</style>
