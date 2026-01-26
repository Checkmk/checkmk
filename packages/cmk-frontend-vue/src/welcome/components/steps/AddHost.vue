<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeCards } from 'cmk-shared-typing/typescript/welcome'
import { type Ref, ref } from 'vue'

import usei18n from '@/lib/i18n'
import usePersistentRef from '@/lib/usePersistentRef'

import CmkAccordionStepPanelItem from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'
import CmkLinkCard from '@/components/CmkLinkCard'
import CmkWizard from '@/components/CmkWizard/CmkWizard.vue'
import CmkWizardButton from '@/components/CmkWizard/CmkWizardButton.vue'
import CmkWizardStep from '@/components/CmkWizard/CmkWizardStep.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import StepCardsRow from '@/welcome/components/steps/components/StepCardsRow.vue'
import StepHeading from '@/welcome/components/steps/components/StepHeading.vue'
import StepParagraph from '@/welcome/components/steps/components/StepParagraph.vue'

import FirstHostSlideout from '../first-host/FirstHostSlideout.vue'
import type { StepId } from './stepComponents'

const { _t } = usei18n()

const cseSlideoutOpen = ref<boolean>(false)

const props = defineProps<{
  step: number
  stepId: StepId
  cards: WelcomeCards
  accomplished: boolean
}>()

const useCseSlideout = ref<boolean>(false)
const currentStep: Ref<number> = usePersistentRef<number>(
  `${props.step}-currentStep`,
  0,
  (v) => v as number,
  'local'
)

if (props.cards.add_host === 'cse-first-host-slideout') {
  useCseSlideout.value = true
}

const emit = defineEmits(['step-completed'])
</script>

<template>
  <CmkAccordionStepPanelItem
    :step="step"
    :disabled="false"
    :accomplished="accomplished"
    :title="_t('Add your first host')"
    :info="_t('2 Steps | Takes 7-10 min')"
  >
    <StepParagraph>
      {{
        _t(
          `In Checkmk, a host is any standalone physical or virtual system that is monitored.
Each host has services which represent what is monitored, for example CPU usage, disk space, processes, or hardware sensors.
The service discovery of Checkmk automatically detects these services.
This allows monitoring to start with minimal configuration effort.`
        )
      }}
    </StepParagraph>

    <CmkWizard v-model="currentStep" mode="guided">
      <CmkWizardStep :index="0" :is-completed="() => currentStep >= 0">
        <template #header>
          <CmkHeading type="h3">{{ _t('Set up basic folder structure') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{
              _t(`In Checkmk, folders are the foundation for organizing hosts and applying settings consistently.
            Creating a folder (or folder structure) before adding your first host helps you keep things tidy from
            the start and makes it easier to manage similar hosts later on through inheritance. Learn more about
            folders and inheritance in the`)
            }}
            <a href="https://docs.checkmk.com/latest/en/hosts_structure.html?lquery=folder#folder">
              {{ _t('documentation.') }}
            </a>
          </StepParagraph>

          <StepCardsRow>
            <CmkLinkCard
              icon-name="newfolder"
              :url="cards.add_folder"
              :title="_t('Add folder')"
              :open-in-new-tab="false"
            />
          </StepCardsRow>
        </template>
        <template #actions>
          <CmkWizardButton type="next" />
        </template>
      </CmkWizardStep>

      <CmkWizardStep :index="1" :is-completed="() => currentStep >= 0">
        <template #header>
          <CmkHeading type="h3">{{ _t('Add your first host') }}</CmkHeading>
        </template>
        <template #content>
          <StepHeading>
            {{ _t('On-premises hosts') }}
          </StepHeading>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="folder"
              :url="useCseSlideout ? undefined : cards.add_host"
              :title="_t('Server (Linux, Windows, Solaris, ...)')"
              :open-in-new-tab="false"
              :callback="
                () => {
                  if (useCseSlideout) {
                    cseSlideoutOpen = true
                  }
                }
              "
            />
            <CmkLinkCard
              icon-name="networking"
              :title="_t('Network devices and SNMP')"
              :url="cards.network_devices"
              :open-in-new-tab="false"
            />
          </StepCardsRow>

          <StepHeading>
            {{ _t('Cloud hosts') }}
          </StepHeading>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="aws-logo"
              :title="_t('Amazon Web Services (AWS)')"
              :url="cards.aws_quick_setup"
              :open-in-new-tab="false"
            />
            <CmkLinkCard
              icon-name="azure-vms"
              :title="_t('Microsoft Azure')"
              :url="cards.azure_quick_setup"
              :open-in-new-tab="false"
            />
            <CmkLinkCard
              icon-name="gcp"
              :title="_t('Google Cloud Platform (GCP)')"
              :url="cards.gcp_quick_setup"
              :open-in-new-tab="false"
            />
          </StepCardsRow>

          <template v-if="cards.synthetic_monitoring || cards.opentelemetry">
            <StepHeading>
              {{ _t('Application monitoring') }}
            </StepHeading>
            <StepCardsRow>
              <CmkLinkCard
                v-if="cards.synthetic_monitoring"
                icon-name="synthetic-monitoring-yellow"
                :title="_t('Synthetic monitoring')"
                :url="cards.synthetic_monitoring"
                :open-in-new-tab="false"
              />
              <CmkLinkCard
                v-if="cards.opentelemetry"
                icon-name="opentelemetry"
                :title="_t('OpenTelemetry (Beta)')"
                :url="cards.opentelemetry"
                :open-in-new-tab="false"
              />
            </StepCardsRow>
          </template>
        </template>
        <template #actions>
          <CmkWizardButton
            v-if="!accomplished && step"
            type="finish"
            :override-label="_t('Mark as done')"
            @click="emit('step-completed', stepId)"
          />
          <CmkWizardButton type="previous" />
        </template>
      </CmkWizardStep>
    </CmkWizard>
  </CmkAccordionStepPanelItem>

  <FirstHostSlideout v-if="useCseSlideout" v-model="cseSlideoutOpen" />
</template>
