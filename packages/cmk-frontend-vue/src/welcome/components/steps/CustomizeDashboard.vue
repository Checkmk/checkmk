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

const { t } = usei18n('welcome-step-5')

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
    :title="t('title', 'Customize dashboard')"
    :info="t('time', '5-7 min')"
  >
    <StepParagraph>
      {{
        t(
          'paragraph',
          'Tailor your monitoring experience by creating a custom dashboard ' +
            'that highlights what matters most to you. ' +
            'Whether you want to track specific hosts, services, or metrics, ' +
            'dashboards help you stay focused and efficient. ' +
            'You can create your own or explore the list of all dashboards to find useful presets.'
        )
      }}
    </StepParagraph>

    <StepCardsRow>
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
    </StepCardsRow>
  </CmkAccordionStepPanelItem>
</template>
