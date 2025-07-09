<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n.ts'
import CmkAccordionStepPanelItem from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'

const { t } = usei18n('welcome-step-1')
</script>

<template>
  <CmkAccordionStepPanelItem
    :step="1"
    :disabled="true"
    :accomplished="true"
    :title="t('title', 'Install Checkmk')"
  />
</template>

<style scoped></style>
