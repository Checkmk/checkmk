<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeCards } from 'cmk-shared-typing/typescript/welcome'

import usei18n from '@/lib/i18n'

import CmkAccordionStepPanelItem from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'
import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkLinkCard from '@/components/CmkLinkCard'

import StepCardsRow from '@/welcome/components/steps/components/StepCardsRow.vue'
import StepParagraph from '@/welcome/components/steps/components/StepParagraph.vue'

import type { StepId } from './utils'

const { _t } = usei18n()

defineProps<{
  step: number
  stepId: StepId
  cards: WelcomeCards
  accomplished: boolean
}>()

const emit = defineEmits(['step-completed'])
</script>

<template>
  <CmkAccordionStepPanelItem
    :step="step"
    :disabled="false"
    :accomplished="accomplished"
    :title="_t('Activate Changes')"
    :info="_t('1 Step | Takes 1-3 min')"
  >
    <StepParagraph>
      {{
        _t(
          `In Checkmk, configuration changes are first saved as pending and do not affect the running monitoring right away.
          This lets you prepare and review multiple changes — such as adding hosts, adjusting services, or fine-tuning
          thresholds — before applying them all at once. Only when you activate the pending changes are they transferred
          to the live monitoring system as a single bundle.`
        )
      }}
    </StepParagraph>
    <CmkAlertBox :heading="_t('Spotting pending changes')">
      {{
        _t(`If there are pending changes, you’ll see a yellow badge on the “Changes” menu item in the main navigation,
      reminding you that your setup is not yet active.`)
      }}
    </CmkAlertBox>

    <StepCardsRow>
      <CmkLinkCard
        icon-name="main-changes"
        :title="_t('Open all pending changes')"
        :url="cards.activate_changes"
        :open-in-new-tab="false"
      />
    </StepCardsRow>

    <CmkButton v-if="!accomplished" variant="primary" @click="emit('step-completed', stepId)">
      <CmkIcon name="check" size="small" variant="inline" /> {{ _t('Mark as done') }}
    </CmkButton>
  </CmkAccordionStepPanelItem>
</template>
