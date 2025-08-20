<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from '../CmkButton.vue'
import { getWizardContext } from '@/components/CmkWizard/utils.ts'
import usei18n from '@/lib/i18n.ts'
import CmkIcon from '@/components/CmkIcon.vue'

export interface CmkWizardButtonProps {
  type: 'next' | 'previous' | 'finish'
  iconName?: string
  iconRotate?: number
  overrideLabel?: string
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
  }
}

function getButtonConfig(
  variant: 'next' | 'prev' | 'save' | unknown,
  iconName: string = '',
  iconRotate: number = 0
): {
  icon: { name: string; rotate: number }
} {
  if (iconName) {
    return { icon: { name: iconName, rotate: iconRotate } }
  }

  switch (variant) {
    case 'previous':
      return { icon: { name: 'continue', rotate: -90 } }

    case 'next':
      return {
        icon: { name: 'continue', rotate: 90 }
      }
    case 'save':
      return {
        icon: { name: 'checkmark', rotate: 0 }
      }
  }
  return { icon: { name: '', rotate: 0 } }
}

const buttonConfig = getButtonConfig(props.type, props.iconName, props.iconRotate)
</script>

<template>
  <CmkButton class="cmk-wizard-button" @click="onClick">
    <CmkIcon :name="buttonConfig.icon.name" :rotate="buttonConfig.icon.rotate" variant="inline" />
    {{ getLabel() }}
  </CmkButton>
</template>

<style scoped>
.cmk-wizard-button {
  width: fit-content;
}
</style>
