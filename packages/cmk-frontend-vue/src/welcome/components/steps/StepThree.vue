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
const { t } = usei18n('step-3')

defineProps<{
  urls: WelcomeUrls
}>()
</script>

<template>
  <CmkAccordionStepPanelItem
    :step="3"
    :disabled="false"
    :accomplished="false"
    :title="t('title', 'Explore your hosts and services')"
    :info="t('time', '5-7 min')"
  >
    <CmkBodyText class="margin-bottom">
      {{
        t(
          'text',
          `Checkmk comes with a range of built-in dashboards that give you a quick overview of your infrastructure
    and help you spot what needs your attention – right out of the box.`
        )
      }}
    </CmkBodyText>

    <b> {{ t('on-premise-hosts', 'View hosts') }}</b>
    <FlexRow>
      <CmkLinkCard
        icon-name="folder"
        :title="t('all-hosts', 'All hosts')"
        :url="urls.all_hosts"
        :open-in-new-tab="false"
      />
      <CmkLinkCard
        icon-name="dashboard"
        :title="t('main-dashboard', 'Main dashboard')"
        :url="urls.main_dashboard"
        :open-in-new-tab="false"
      />
    </FlexRow>

    <b> {{ t('investigate-problems', 'Investigate problems') }}</b>
    <FlexRow>
      <CmkLinkCard
        icon-name="dashboard-problems"
        :title="t('problem-dashboard', 'Problem dashboard')"
        :url="urls.problem_dashboard"
        :open-in-new-tab="false"
      />
      <CmkLinkCard
        icon-name="svc-problems"
        :title="t('unhandled-service-problems', 'Unhandled service problems')"
        :url="urls.unhandled_service_problems"
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
