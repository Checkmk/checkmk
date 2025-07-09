<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeUrls } from 'cmk-shared-typing/typescript/welcome'
import CmkLinkCard from '@/components/CmkLinkCard.vue'
import CmkBodyText from '@/components/typography/CmkBodyText.vue'
import usei18n from '@/lib/i18n.ts'
import FlexRow from '@/welcome/components/steps/FlexRow.vue'
import CmkAccordionStepPanelItem from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'
const { t } = usei18n('welcome-step-5')

defineProps<{
  urls: WelcomeUrls
}>()
</script>

<template>
  <CmkAccordionStepPanelItem
    :step="5"
    :disabled="false"
    :accomplished="false"
    :title="t('title', 'Customize dashboard')"
    :info="t('time', '5-7 min')"
  >
    <CmkBodyText class="margin-bottom">
      {{ t('text', 'TBD') }}
    </CmkBodyText>

    <FlexRow>
      <CmkLinkCard
        icon-name="new"
        :title="t('add-custom-dashboard', 'Add custom dashboard')"
        :url="urls.add_custom_dashboard"
        :open-in-new-tab="false"
      />
      <CmkLinkCard
        icon-name="dashboard"
        :title="t('list-of-all-dashboards', 'List of all dashboards')"
        :url="urls.all_dashboards"
        :open-in-new-tab="false"
      />
    </FlexRow>
  </CmkAccordionStepPanelItem>
</template>

<style scoped>
.margin-bottom {
  margin-bottom: var(--spacing);
}
</style>
