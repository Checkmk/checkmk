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
import StepHeading from '@/welcome/components/steps/components/StepHeading.vue'
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
    :title="_t('Add your first host')"
    :info="_t('2-5 min')"
  >
    <StepParagraph>
      {{
        _t(
          `Each host includes a number of services that represent what you want to monitor, for example,
  CPU usage, disk space, running processes, or hardware sensors. Checkmk makes this easy with the
  Service Discovery, which automatically detects relevant services on your host, so you can start
  monitoring with minimal setup.`
        )
      }}
    </StepParagraph>

    <StepHeading>
      {{ _t('On-premise-hosts') }}
    </StepHeading>
    <StepCardsRow>
      <CmkLinkCard
        icon-name="folder"
        :title="_t('Server (Linux, Windows, Solaris, ...)')"
        :url="urls.add_host"
        :open-in-new-tab="false"
      />
      <CmkLinkCard
        icon-name="networking"
        :title="_t('Network devices and SNMP')"
        :url="urls.network_devices"
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
        :url="urls.aws_quick_setup"
        :open-in-new-tab="false"
      />
      <CmkLinkCard
        icon-name="azure-vms"
        :title="_t('Microsoft Azure')"
        :url="urls.azure_quick_setup"
        :open-in-new-tab="false"
      />
      <CmkLinkCard
        icon-name="gcp"
        :title="_t('Google Cloud Platform (GCP)')"
        :url="urls.gcp_quick_setup"
        :open-in-new-tab="false"
      />
    </StepCardsRow>

    <template v-if="urls.synthetic_monitoring || urls.opentelemetry">
      <StepHeading>
        {{ _t('Application monitoring') }}
      </StepHeading>
      <StepCardsRow>
        <CmkLinkCard
          v-if="urls.synthetic_monitoring"
          icon-name="synthetic-monitoring-yellow"
          :title="_t('Synthetic monitoring')"
          :url="urls.synthetic_monitoring"
          :open-in-new-tab="false"
        />
        <CmkLinkCard
          v-if="urls.opentelemetry"
          icon-name="opentelemetry"
          :title="_t('OpenTelemetry (Beta)')"
          :url="urls.opentelemetry"
          :open-in-new-tab="false"
        />
      </StepCardsRow>
    </template>
  </CmkAccordionStepPanelItem>
</template>
