<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from '@/lib/i18nString'

import type { ButtonVariants } from '@/components/CmkButton.vue'
import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon'
import type { SimpleIcons } from '@/components/CmkIcon'

interface ActionButtonIcon {
  name: SimpleIcons
  side?: 'left' | 'right'
  rotate?: number
}

interface ActionButtonProps {
  label: TranslatedString
  variant: ButtonVariants['variant']
  icon?: ActionButtonIcon
  action: () => void
}

defineProps<ActionButtonProps>()
</script>

<template>
  <CmkButton :variant="variant" @click="action">
    <span v-if="!icon || icon?.side === 'right'">{{ label }}{{ '\xa0' }}</span>
    <CmkIcon v-if="icon" :name="icon.name" :rotate="icon.rotate || 0" variant="inline" />
    <span v-if="icon?.side === 'left'">{{ '\xa0' }}{{ label }}</span>
  </CmkButton>
</template>
