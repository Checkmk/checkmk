<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One group of properties on the object card: its heading, and the rows below it.

A section whose fields most objects never touch can fold itself away instead,
and then starts open only when the object already carries a value in it.
-->
<script setup lang="ts">
import { CmkCollapsibleTitle } from 'cmk-ui-library/components/CmkCollapsible'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { ref } from 'vue'

const props = defineProps<{
  title: TranslatedString
  collapsible?: boolean
  /** Only read for a collapsible section, and only for its initial state. */
  defaultOpen?: boolean
  /** Shown beside a collapsible heading, so a folded section still says what it holds. */
  sideTitle?: TranslatedString
}>()

const open = ref(props.defaultOpen === true)
</script>

<template>
  <section class="maps-property-section">
    <CmkCollapsibleTitle
      v-if="collapsible"
      :title="title"
      :side-title="sideTitle ?? untranslated('')"
      :open="open"
      @toggle-open="open = !open"
    />
    <CmkHeading v-else type="h4" class="maps-property-section__title">{{ title }}</CmkHeading>
    <div
      v-if="!collapsible || open"
      class="maps-property-section__rows"
      :class="collapsible ? 'maps-property-section__rows--collapsed-head' : ''"
    >
      <slot />
    </div>
  </section>
</template>

<style scoped>
.maps-property-section {
  margin-bottom: var(--dimension-6);
}

/* Outspecifies ``CmkHeading``'s own ``margin: 0``, which is at equal
   specificity and would otherwise win on source order. */
.maps-property-section > .maps-property-section__title {
  margin-bottom: var(--dimension-4);
  color: var(--font-color-dimmed);
}

.maps-property-section__rows {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

/* The collapsible head carries no bottom margin of its own. */
.maps-property-section__rows--collapsed-head {
  margin-top: var(--dimension-4);
}
</style>
