<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import CmkLinkCard from 'cmk-ui-library/components/CmkLinkCard'
import StateTag from 'cmk-ui-library/components/StateTag.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import { ref } from 'vue'

defineProps<{ screenshotMode: boolean }>()
const bordersSelected = ref<'standard' | 'borderless'>('standard')
const contrastSelected = ref<'standard' | 'high'>('standard')
</script>

<template>
  <label>Borders: </label>
  <CmkDropdown
    v-model="bordersSelected"
    :options="{
      type: 'fixed',
      suggestions: [
        { name: 'standard', title: 'Standard' },
        { name: 'borderless', title: 'Borderless' }
      ]
    }"
    input-hint="some input hint"
    no-results-hint="no results hint"
    label="some label"
    required
  />
  <br />
  <label>Contrast: </label>
  <CmkDropdown
    v-model="contrastSelected"
    :options="{
      type: 'fixed',
      suggestions: [
        { name: 'standard', title: 'Standard' },
        { name: 'high', title: 'High' }
      ]
    }"
    input-hint="some input hint"
    no-results-hint="no results hint"
    label="some label"
    required
  />
  <br /><br /><br />
  <CmkLinkCard
    title="Checkmk website"
    icon-name="checkmk-logo-min"
    subtitle="Have a look at our website for more information about Checkmk."
    url="https://checkmk.com"
    :borders="bordersSelected"
    :contrast="contrastSelected"
    :open-in-new-tab="true"
  />
  <CmkLinkCard
    title="Ask Checkmk AI"
    subtitle="Your assistant for Checkmk – ask anything from setup to troubleshooting."
    url="https://chat.checkmk.com"
    :borders="bordersSelected"
    :contrast="contrastSelected"
    :open-in-new-tab="true"
  />
  <CmkLinkCard
    title="Demo App Home"
    icon-name="about-checkmk"
    url=""
    :open-in-new-tab="false"
    :borders="bordersSelected"
    :contrast="contrastSelected"
  />

  <CmkLinkCard
    title="Disabled"
    icon-name="checkmk-logo-min"
    url="https://checkmk.com"
    :borders="bordersSelected"
    :contrast="contrastSelected"
    :disabled="true"
    :open-in-new-tab="false"
  />

  <CmkLinkCard
    title="Without a link"
    subtitle="A card with neither url nor callback is a plain container: no hover, no focus ring."
    :borders="bordersSelected"
    :contrast="contrastSelected"
    :open-in-new-tab="false"
  >
    <template #leading>
      <StateTag label="UP" tone="ok" kind="host" class="ucl-cmk-link-card-dev__leading" />
    </template>
    <CmkParagraph>Anything the card should carry below its subtitle goes here.</CmkParagraph>
  </CmkLinkCard>
</template>

<style scoped>
.ucl-cmk-link-card-dev__leading {
  align-self: flex-start;
  margin-right: var(--dimension-6);
}
</style>
