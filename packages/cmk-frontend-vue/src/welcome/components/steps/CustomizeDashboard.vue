<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeUrls } from 'cmk-shared-typing/typescript/welcome'

import usei18n from '@/lib/i18n.ts'

import CmkAccordionStepPanelItem from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'
import CmkLinkCard from '@/components/CmkLinkCard.vue'

import StepCardsRow from '@/welcome/components/steps/components/StepCardsRow.vue'
import StepParagraph from '@/welcome/components/steps/components/StepParagraph.vue'

const { _t } = usei18n()

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
    :title="_t('Customize dashboard')"
    :info="_t('5-7 min')"
  >
    <StepParagraph>
      {{
        _t(
          `Tailor your monitoring experience by creating a custom dashboard
            that highlights what matters most to you.
            Whether you want to track specific hosts, services, or metrics,
            dashboards help you stay focused and efficient.
            You can create your own or explore the list of all dashboards to find useful presets.`
        )
      }}
    </StepParagraph>

    <StepCardsRow>
      <CmkLinkCard
        icon-name="new"
        :title="_t('Add custom dashboard')"
        :url="urls.add_custom_dashboard"
        :open-in-new-tab="false"
      />
      <CmkLinkCard
        icon-name="dashboard"
        :title="_t('List of all dashboards')"
        :url="urls.all_dashboards"
        :open-in-new-tab="false"
      />
    </StepCardsRow>
  </CmkAccordionStepPanelItem>
</template>
