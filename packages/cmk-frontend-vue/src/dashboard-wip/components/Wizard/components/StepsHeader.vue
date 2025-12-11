<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkIcon from '@/components/CmkIcon'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

const { _t } = usei18n()

interface StepsHeaderProps {
  title: TranslatedString
  subtitle?: TranslatedString
  hideBackButton?: boolean
  closeButton?: boolean
}

const emit = defineEmits(['back'])

defineProps<StepsHeaderProps>()
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
        <CmkHeading type="h1">
          {{ title }}
        </CmkHeading>
      </div>
      <CmkLabel v-if="subtitle" variant="subtitle">{{ subtitle }}</CmkLabel>
    </div>
    <button v-if="closeButton" type="button" class="db-steps-header__close" @click="emit('back')">
      <CmkIcon :aria-label="_t('Close')" name="close" size="xsmall" />
    </button>
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

.db-steps-header__container:has(.db-steps-header__close):not(:has(.db-steps-header__icon)) {
  justify-content: space-between;
  padding-top: 0;
}

.db-steps-header__icon {
  padding-left: var(--dimension-2);
  padding-right: var(--dimension-4);
  cursor: pointer;
}

.db-steps-header__label:has(.db-steps-header__icon) {
  padding-left: var(--spacing);
}

.db-steps-header__close {
  background: none;
  border: none;
  margin: 0;
  padding: 0;
}
</style>
