<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkIcon, { type CmkIconVariants } from '@/components/CmkIcon'
import type { SimpleIcons } from '@/components/CmkIcon'
import { getWizardContext } from '@/components/CmkWizard/utils.ts'

import CmkButton, { type ButtonVariants } from '../CmkButton.vue'

export interface CmkWizardButtonProps {
  type: 'next' | 'previous' | 'finish' | 'other'
  iconName?: SimpleIcons | undefined
  iconRotate?: number
  overrideLabel?: TranslatedString
}

const { _t } = usei18n()
const context = getWizardContext()
const props = defineProps<CmkWizardButtonProps>()

function onClick() {
  switch (props.type) {
    case 'next':
      context.navigation.next()
      break
    case 'previous':
      context.navigation.prev()
      break
  }
}

function getLabel() {
  if (props.overrideLabel) {
    return props.overrideLabel
  }
  switch (props.type) {
    case 'next':
      return _t('Next step')
    case 'previous':
      return _t('Previous step')
    case 'finish':
      return _t('Finish')
    default:
      return ''
  }
}

function getButtonConfig(
  variant: 'next' | 'previous' | 'finish' | unknown,
  iconName: SimpleIcons | undefined,
  iconRotate: number = 0
): {
  variant?: ButtonVariants['variant']
  icon: { name: SimpleIcons; rotate: number }
  iconSize?: CmkIconVariants['size']
} {
  let icon: { name: SimpleIcons; rotate: number } = {
    name: 'continue',
    rotate: 0
  }

  if (iconName) {
    icon = { name: iconName, rotate: iconRotate }
  }

  switch (variant) {
    case 'other':
      return {
        variant: 'secondary',
        icon
      }
    case 'previous':
      return {
        icon: { name: 'continue', rotate: -90 }
      }
    case 'next':
      return {
        variant: 'secondary',
        icon: { name: 'continue', rotate: 90 }
      }
    case 'finish':
      return {
        variant: 'primary',
        icon: { name: 'check', rotate: 0 },
        iconSize: 'small'
      }
    default:
      throw new Error(`Unknown button variant: ${variant}`)
  }
}

const buttonConfig = getButtonConfig(props.type, props.iconName, props.iconRotate)
</script>

<template>
  <CmkButton class="cmk-wizard-button" :variant="buttonConfig.variant" @click="onClick">
    <CmkIcon
      :name="buttonConfig.icon.name"
      :size="buttonConfig.iconSize"
      :rotate="buttonConfig.icon.rotate"
      variant="inline"
    />
    {{ getLabel() }}
  </CmkButton>
</template>

<style scoped>
.cmk-wizard-button {
  width: fit-content;
}
</style>
