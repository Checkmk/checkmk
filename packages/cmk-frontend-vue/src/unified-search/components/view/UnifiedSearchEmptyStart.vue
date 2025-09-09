<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon.vue'
import CmkKeyboardKey from '@/components/CmkKeyboardKey.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

const { _t } = usei18n()
</script>

<template>
  <div class="unified-search-empty-start">
    <CmkIcon class="unified-search-empty-start__icon" name="search" size="xxxlarge"></CmkIcon>
    <CmkHeading class="unified-search-empty-start__heading" type="h2">{{
      _t('Find rules, hosts, dashboards, settings ...')
    }}</CmkHeading>
    <CmkParagraph
      >{{ _t('Tip: Press') }}
      <CmkKeyboardKey keyboard-key="/" size="small"></CmkKeyboardKey>
      {{
        _t('to view all search operator and, e.g., find all hosts with the same host label (hl:)')
      }}</CmkParagraph
    >
  </div>
</template>

<style scoped>
.unified-search-empty-start {
  opacity: 0.8;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;

  .unified-search-empty-start__icon {
    margin-top: calc(-2 * var(--dimension-10));
    margin-bottom: var(--dimension-10);
    opacity: 0.1;

    &:hover {
      opacity: 0.1 !important;
    }
  }

  .unified-search-empty-start__heading {
    margin-bottom: var(--dimension-5);
  }
}
</style>
