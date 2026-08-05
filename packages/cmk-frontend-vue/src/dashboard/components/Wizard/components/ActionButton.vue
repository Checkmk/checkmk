<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { ButtonIcon, ButtonVariants } from 'cmk-ui-library/components/CmkButton'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

interface ActionButtonProps {
  label: TranslatedString
  variant?: ButtonVariants['variant']
  icon?: ButtonIcon
  action: () => void
}

defineProps<ActionButtonProps>()
</script>

<template>
  <CmkButton :variant="variant" :icon="icon" @click="action">
    {{ label }}
  </CmkButton>
</template>
