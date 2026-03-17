<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkTabs, { CmkTab, CmkTabContent } from '@/components/CmkTabs'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

const { _t } = usei18n()

const activeTab = ref('grpc')
</script>

<template>
  <CmkTabs v-model="activeTab">
    <template #tabs>
      <CmkTab id="grpc">{{ _t('GRPC') }}</CmkTab>
      <CmkTab id="http">{{ _t('HTTP') }}</CmkTab>
    </template>
    <template #tab-contents>
      <CmkTabContent id="grpc">
        <CmkParagraph>{{
          _t('Configure a GRPC-based OTLP receiver that will collect OpenTelemetry data.')
        }}</CmkParagraph>
      </CmkTabContent>
      <CmkTabContent id="http">
        <CmkParagraph>{{
          _t('Configure an HTTP-based OTLP receiver that will collect OpenTelemetry data.')
        }}</CmkParagraph>
      </CmkTabContent>
    </template>
  </CmkTabs>
</template>
