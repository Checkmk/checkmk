<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from '@/lib/i18nString'

import CmkIconButton from '@/components/CmkIconButton.vue'
import CmkLabel from '@/components/CmkLabel.vue'

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
    <div v-if="!hideBackButton" class="db-steps-header__icon">
      <CmkIconButton
        name="back"
        variant="plain"
        size="xxlarge"
        :colored="false"
        @click="() => emit('back')"
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

.db-steps-header__icon {
  position: relative;
  left: -3px;
}

.db-steps-header__container {
  display: flex;
}

.db-steps-header__label {
  padding-left: var(--spacing);
}
</style>
