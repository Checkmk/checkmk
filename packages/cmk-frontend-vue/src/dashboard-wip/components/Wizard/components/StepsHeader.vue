<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkLabel from '@/components/CmkLabel.vue'

const { _t } = usei18n()

interface BackButtonProps {
  title: TranslatedString
  subtitle?: TranslatedString
  hideBackButton?: boolean
}

const emit = defineEmits(['back'])

defineProps<BackButtonProps>()
</script>

<template>
  <div class="db-steps-header__container">
    <div v-if="!hideBackButton" @click="emit('back')">
      <CmkMultitoneIcon
        name="back"
        :title="_t('Back')"
        size="xlarge"
        primary-color="font"
        class="db-steps-header__icon"
      />
    </div>
    <div class="db-steps-header__label">
      <div class="db-steps-header__title-block">
        <CmkLabel variant="title">{{ title }}</CmkLabel>
      </div>
      <CmkLabel v-if="subtitle" variant="subtitle">{{ subtitle }}</CmkLabel>
    </div>
  </div>
</template>

<style scoped>
.db-steps-header__title-block {
  break-after: always;
}

.db-steps-header__container {
  display: flex;
  padding-top: var(--dimension-4);
}

.db-steps-header__icon {
  padding-left: var(--dimension-2);
  padding-right: var(--dimension-4);
  cursor: pointer;
}

.db-steps-header__label {
  padding-left: var(--spacing);
}
</style>
