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

const { _t } = usei18n()

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
    :title="_t('Adjust services')"
    :info="_t('5-7 min')"
  >
    <StepParagraph>
      {{
        _t(
          `Each service in Checkmk comes with default parameter values.
            You can customize these to match your monitoring needs,
            most commonly by setting thresholds for WARN and CRIT states using rules.
            To find the right ruleset for a service, start with the Service Discovery page.`
        )
      }}
    </StepParagraph>

    <CmkWizard mode="overview">
      <CmkWizardStep>
        <template #header>
          <CmkHeading type="h3">{{ _t('Run a service discovery') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{ _t('To adjust parameters for a host, start by running a service discovery.') }}
            <br />
            {{ _t('In the host table, click on the') }}
            <CmkIcon name="services" variant="inline" size="small" />{{
              _t('-icon next to the host to open the service discovery.')
            }}
          </StepParagraph>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="folder"
              :title="_t('View host table')"
              :url="props.urls.setup_hosts"
              :open-in-new-tab="false"
            />
          </StepCardsRow>
        </template>
      </CmkWizardStep>

      <CmkWizardStep>
        <template #header>
          <CmkHeading type="h3">{{ _t('Open the ruleset for a check parameter') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{ _t('In the Service Discovery view, find the service you want to configure.') }}
            <br />
            {{ _t('Click the') }}
            <CmkIcon name="check_parameters" variant="inline" size="small" />{{
              _t('-icon next to it to open the corresponding ruleset.')
            }}
          </StepParagraph>
        </template>
      </CmkWizardStep>

      <CmkWizardStep>
        <template #header>
          <CmkHeading type="h3">{{ _t('Create a check parameter rule') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{
              _t(
                'In the ruleset view, click Add rule for current host to create a rule that applies specifically to the selected host.'
              )
            }}
            <br />
            {{
              _t('You can now define custom parameters like thresholds or other check settings.')
            }}
          </StepParagraph>
        </template>
      </CmkWizardStep>

      <CmkWizardStep>
        <template #header>
          <CmkHeading type="h3">{{ _t('Activate changes') }}</CmkHeading>
        </template>
        <template #content>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="main_changes"
              :title="_t('Activate changes')"
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
