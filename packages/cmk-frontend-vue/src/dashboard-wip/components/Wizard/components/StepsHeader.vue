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
}

const emit = defineEmits(['back'])

defineProps<BackButtonProps>()
</script>

<template>
  <div class="back-button__container">
    <div class="back-button__icon">
      <CmkIconButton
        name="back"
        variant="plain"
        size="xxlarge"
        :colored="false"
        @click="() => emit('back')"
      />
    </div>
    <div class="back-button__label">
      <CmkLabel variant="title">{{ title }}</CmkLabel>
      <CmkLabel v-if="subtitle" variant="subtitle">{{ subtitle }}</CmkLabel>
    </div>
  </div>
</template>

<style scoped>
.back-button__icon {
  position: relative;
  left: -3px;
}

.back-button__container {
  display: flex;
}

.back-button__label {
  padding-left: var(--spacing);
}
</style>
