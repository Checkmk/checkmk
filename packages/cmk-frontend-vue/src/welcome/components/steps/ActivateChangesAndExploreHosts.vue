<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeUrls } from 'cmk-shared-typing/typescript/welcome'
import CmkLinkCard from '@/components/CmkLinkCard.vue'
import usei18n from '@/lib/i18n.ts'
import StepCardsRow from '@/welcome/components/steps/components/StepCardsRow.vue'
import CmkAccordionStepPanelItem from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'
import StepParagraph from '@/welcome/components/steps/components/StepParagraph.vue'
import StepHeading from '@/welcome/components/steps/components/StepHeading.vue'

const { t } = usei18n('welcome-step-3')

defineProps<{
  step: number
  urls: WelcomeUrls
  accomplished: boolean
}>()
</script>

<template>
  <CmkAccordionStepPanelItem
    :step="step"
    :disabled="false"
    :accomplished="accomplished"
    :title="t('title', 'Activate changes and explore your hosts')"
    :info="t('time', '5-7 min')"
  >
    <StepParagraph>
      {{
        t(
          'paragraph-1',
          'After adding hosts and discovering services, ' +
            'you need to activate your changes to apply the configuration.'
        )
      }}
    </StepParagraph>
    <StepParagraph>
      {{
        t(
          'paragraph-2',
          'Once done, dive into your monitoring data: get an overview of all hosts, ' +
            'check the problem dashboard for critical issues, ' +
            'or focus on unhandled service problems to start troubleshooting.'
        )
      }}
    </StepParagraph>

    <StepHeading>
      {{ t('activate-changes', 'Activate changes') }}
    </StepHeading>
    <StepCardsRow>
      <CmkLinkCard
        icon-name="main_changes"
        :title="t('activate-changes', 'Activate pending changes')"
        :url="urls.activate_changes"
        :open-in-new-tab="false"
      />
    </StepCardsRow>

    <StepHeading>
      {{ t('explore-host', 'Explore hosts') }}
    </StepHeading>
    <StepCardsRow>
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
      <CmkLinkCard
        icon-name="dashboard-problems"
        :title="t('problem-dashboard', 'Problem dashboard')"
        :url="urls.problem_dashboard"
        :open-in-new-tab="false"
      />
    </StepCardsRow>
  </CmkAccordionStepPanelItem>
</template>
