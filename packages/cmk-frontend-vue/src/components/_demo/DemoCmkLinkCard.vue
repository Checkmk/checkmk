<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkLinkCard from '@/components/CmkLinkCard.vue'
import CmkDropdown from '@/components/CmkDropdown.vue'
import { ref } from 'vue'

defineProps<{ screenshotMode: boolean }>()
const variantSelected = ref<'standard' | 'borderless'>('standard')
</script>

<template>
  <label>Variant: </label>
  <CmkDropdown
    v-model:selected-option="variantSelected"
    :options="{
      type: 'fixed',
      suggestions: [
        { name: 'standard', title: 'Standard' },
        { name: 'borderless', title: 'Borderless' }
      ]
    }"
    input-hint="some input hint"
    no-results-hint="no results hint"
    required-text="required"
    label="some label"
  />
  <br /><br /><br />
  <CmkLinkCard
    title="Checkmk website"
    icon-name="checkmk-logo-min"
    subtitle="Have a look at our website for more information about Checkmk."
    url="https://checkmk.com"
    :variant="variantSelected"
    :open-in-new-tab="true"
  />
  <CmkLinkCard
    title="Ask Checkmk AI"
    subtitle="Your assistant for Checkmk – ask anything from setup to troubleshooting."
    url="https://chat.checkmk.com"
    :variant="variantSelected"
    :open-in-new-tab="true"
  />
  <CmkLinkCard
    title="Demo App Home"
    icon-name="about-checkmk"
    url=""
    :open-in-new-tab="false"
    :variant="variantSelected"
  />

  <CmkLinkCard
    title="Disabled"
    icon-name="checkmk-logo-min"
    url="https://checkmk.com"
    :variant="variantSelected"
    :disabled="true"
    :open-in-new-tab="false"
  />
</template>

<style scoped></style>
