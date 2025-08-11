<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeUrls } from 'cmk-shared-typing/typescript/welcome'
import CmkLinkCard from '@/components/CmkLinkCard.vue'
import CmkIcon from '@/components/CmkIcon.vue'
import usei18n from '@/lib/i18n.ts'
import StepCardsRow from '@/welcome/components/steps/components/StepCardsRow.vue'
import CmkAccordionStepPanelItem from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'
import StepParagraph from '@/welcome/components/steps/components/StepParagraph.vue'
import CmkWizard from '@/components/CmkWizard/CmkWizard.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkWizardStep from '@/components/CmkWizard/CmkWizardStep.vue'

const { t } = usei18n('welcome-step-3')

const props = defineProps<{
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
    :title="t('title', 'Adjust services')"
    :info="t('time', '5-7 min')"
  >
    <StepParagraph>
      {{
        t(
          'adjust-services-step-intro',
          'Each service in Checkmk comes with default parameter values. ' +
            'You can customize these to match your monitoring needs, ' +
            'most commonly by setting thresholds for WARN and CRIT states using rules. ' +
            'To find the right ruleset for a service, start with the Service Discovery page.'
        )
      }}
    </StepParagraph>

    <CmkWizard mode="overview">
      <CmkWizardStep>
        <template #header>
          <CmkHeading type="h3">{{ t('stage-0-title', 'Run a service discovery') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{
              t(
                'stage-0-instruction-1',
                'To adjust parameters for a host, start by running a service discovery.'
              )
            }}
            <br />
            {{ t('stage-0-instruction-2', 'In the host table, click on the') }}
            <CmkIcon name="services" variant="inline" size="small" />{{
              t('stage-0-instruction-3', '-icon next to the host to open the service discovery.')
            }}
          </StepParagraph>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="folder"
              :title="t('view-host-table', 'View host table')"
              :url="props.urls.setup_hosts"
              :open-in-new-tab="false"
            />
          </StepCardsRow>
        </template>
      </CmkWizardStep>

      <CmkWizardStep>
        <template #header>
          <CmkHeading type="h3">{{
            t('stage-1-title', 'Open the ruleset for a check parameter')
          }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{
              t(
                'stage-1-instruction-1',
                'In the Service Discovery view, find the service you want to configure.'
              )
            }}
            <br />
            {{ t('stage-1-instruction-2', 'Click the') }}
            <CmkIcon name="check_parameters" variant="inline" size="small" />{{
              t('stage-1-instruction-3', '-icon next to it to open the corresponding ruleset.')
            }}
          </StepParagraph>
        </template>
      </CmkWizardStep>

      <CmkWizardStep>
        <template #header>
          <CmkHeading type="h3">{{
            t('stage-2-title', 'Create a check parameter rule')
          }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{
              t(
                'stage-2-instruction-1',
                'In the ruleset view, click Add rule for current host to create a rule that applies specifically to the selected host.'
              )
            }}
            <br />
            {{
              t(
                'stage-2-instruction-2',
                'You can now define custom parameters like thresholds or other check settings.'
              )
            }}
          </StepParagraph>
        </template>
      </CmkWizardStep>

      <CmkWizardStep>
        <template #header>
          <CmkHeading type="h3">{{ t('stage-3-title', 'Activate changes') }}</CmkHeading>
        </template>
        <template #content>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="main_changes"
              :title="t('activate-changes', 'Activate changes')"
              :url="props.urls.activate_changes"
              :open-in-new-tab="false"
            />
          </StepCardsRow>
        </template>
      </CmkWizardStep>
    </CmkWizard>
  </CmkAccordionStepPanelItem>
</template>

<style scoped></style>
