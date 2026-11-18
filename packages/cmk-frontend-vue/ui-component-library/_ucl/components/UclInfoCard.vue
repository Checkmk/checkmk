<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

interface UclInfoCardProps {
  iconName?: SimpleIcons | undefined
  title: TranslatedString
  subtitle?: TranslatedString
  bulletPoints?: TranslatedString[]
}

const { iconName, title, subtitle, bulletPoints = [] } = defineProps<UclInfoCardProps>()
</script>

<template>
  <div class="ucl-info-card">
    <div class="ucl-info-card__header">
      <CmkIcon v-if="iconName" :name="iconName" size="xxlarge" class="ucl-info-card__header-icon" />
      <CmkHeading type="h4" class="ucl-info-card__heading">{{ title }}</CmkHeading>
    </div>

    <div class="ucl-info-card__content">
      <CmkParagraph v-if="subtitle" class="ucl-info-card__subtitle">
        {{ subtitle }}
      </CmkParagraph>

      <ul v-if="bulletPoints.length" class="ucl-info-card__list">
        <li v-for="(point, index) in bulletPoints" :key="index" class="ucl-info-card__list-item">
          {{ point }}
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.ucl-info-card {
  display: flex;
  flex-direction: column;
  border-radius: var(--border-radius);
  padding: var(--dimension-6);
  gap: var(--dimension-5);
  background-color: var(--ucl-elements-background-color);
}

.ucl-info-card__header {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  justify-content: center;
}

.ucl-info-card__header-icon {
  flex-shrink: 0;
  color: var(--ucl-body-text-color);
}

.ucl-info-card__subtitle {
  color: var(--font-color-dimmed);
  margin-bottom: var(--dimension-4);
}

.ucl-info-card__list {
  margin: 0;
  padding-left: var(--dimension-8);
  list-style-type: disc;
}

.ucl-info-card__list-item {
  color: var(--ucl-body-text-color);
  line-height: 1.6;
  margin-bottom: var(--dimension-3);
}

.ucl-info-card__list-item:last-child {
  margin-bottom: 0;
}
</style>
