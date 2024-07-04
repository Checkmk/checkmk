<script setup lang="ts">
import { Button } from '@/components/ui/button'

interface CustomIconButtonProps {
  /** @property {string} iconUrl - Url of the icon to be displayed inside the button */
  iconUrl: string

  /** @property {string} label - Button's caption */
  label: string

  /** @property {string} ariaLabel - Aria label for the button */
  ariaLabel?: string
}

type ButtonVariant = 'prev' | 'next' | 'back' | 'save'

interface PredefinedIconButtonProps {
  /** @property {string} variant - Type of button */
  variant: ButtonVariant

  /** @property {string} label - Button's caption */
  label: string

  /** @property {string} ariaLabel - Aria label for the button */
  ariaLabel?: string
}

export type IconButtonProps = CustomIconButtonProps | PredefinedIconButtonProps

const props = defineProps<IconButtonProps>()
defineEmits(['click'])

let selectedAriaLabel = ''
let selectedIconUrl = ''

const processPrefedinedIconButtonProps = (props: PredefinedIconButtonProps) => {
  switch (props.variant) {
    case 'prev':
      selectedAriaLabel = 'Go to the previous stage'
      selectedIconUrl = 'themes/facelift/images/icon_up.png'
      break
    case 'next':
      selectedAriaLabel = 'Go to the next stage'
      selectedIconUrl = 'themes/facelift/images/icon_continue.png'
      break
    case 'back':
      selectedAriaLabel = 'Go back'
      selectedIconUrl = 'themes/facelift/images/icon_back_arrow.png'
      break
    case 'save':
      selectedAriaLabel = 'Save'
      selectedIconUrl = 'themes/facelift/images/icon_save_to_services.svg'
      break
  }
}

const processCustomIconButtonProps = (props: CustomIconButtonProps) => {
  selectedAriaLabel = props.ariaLabel || ''
  selectedIconUrl = props.iconUrl
}

if ('variant' in props && props?.variant) {
  processPrefedinedIconButtonProps(props as PredefinedIconButtonProps)
} else {
  processCustomIconButtonProps(props as CustomIconButtonProps)
}
</script>

<template>
  <Button class="cmk-icon-button button" :aria-label="selectedAriaLabel" @click="$emit('click')">
    <img :src="selectedIconUrl" height="16" />
    <span>&nbsp; {{ props.label }}</span>
  </Button>
</template>

<style scoped>
.cmk-icon-button img {
  position: relative;
  top: 2px;
}

.cmk-icon-button span {
  position: relative;
  top: -2px;
}
</style>
