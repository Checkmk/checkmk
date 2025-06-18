<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkHeading1 from '@/components/typography/CmkHeading1.vue'
import CmkBody from '@/components/typography/CmkBodyText.vue'
import StepsProgressBar, { type StepsProgressBarProps } from './StepsProgressBar.vue'
const { t } = usei18n('welcome-banner')

const { completedSteps = 1, totalSteps = 5 } = defineProps<StepsProgressBarProps>()
</script>

<template>
  <section class="welcome-banner">
    <CmkIcon name="checkmk-logo-min" size="xxxlarge" />
    <div class="welcome-banner__content">
      <CmkHeading1 class="welcome-banner__title">
        {{ t('title', 'Welcome to Checkmk!') }}
      </CmkHeading1>
      <CmkBody class="welcome-banner__subtitle">
        {{ t('subtitle', 'Get started with Checkmk in 5 easy steps.') }}
      </CmkBody>
      <StepsProgressBar :completed-steps="completedSteps" :total-steps="totalSteps" />
    </div>
  </section>
</template>

<style scoped>
.welcome-banner {
  display: flex;
  align-items: center;
  gap: 40px;
  justify-content: flex-start;
  padding: 40px 32px;
  border-radius: var(--border-radius);
  background: linear-gradient(
    90deg,
    var(--default-bg-color) 0%,
    var(--color-corporate-green-60) 100%
  );
  height: 100%;
}

.welcome-banner__content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.welcome-banner__title {
  margin: 0 0 4px 0;
}

.welcome-banner__subtitle {
  margin: 0 0 12px 0;
}
</style>
