<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One group of properties on the object card: its heading, and the rows below it.

A section whose fields most objects never touch can fold itself away instead,
and then starts open only when the object already carries a value in it.

A section that is switched on and off as a whole carries that switch in its
heading (the ``title-control`` slot), and its rows are indented below it, the
way a FormSpec renders the elements of an optional dictionary entry.
-->
<script setup lang="ts">
import { CmkCollapsibleTitle } from 'cmk-ui-library/components/CmkCollapsible'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { ref } from 'vue'

const props = defineProps<{
  title: TranslatedString
  collapsible?: boolean
  /** Only read for a collapsible section, and only for its initial state. */
  defaultOpen?: boolean
  /** Hides the rows, e.g. while the heading's switch is off. */
  empty?: boolean
}>()

const open = ref(props.defaultOpen === true)
</script>

<template>
  <section class="maps-property-section">
    <CmkCollapsibleTitle
      v-if="collapsible"
      :title="title"
      :open="open"
      @toggle-open="open = !open"
    />
    <div v-else class="maps-property-section__head">
      <CmkHeading type="h4" class="maps-property-section__title">{{ title }}</CmkHeading>
      <slot name="title-control" />
    </div>
    <div
      v-if="(!collapsible || open) && !empty"
      class="maps-property-section__rows"
      :class="{ 'maps-property-section__rows--collapsed-head': collapsible }"
    >
      <slot />
    </div>
  </section>
</template>

<style scoped>
.maps-property-section {
  margin-bottom: var(--dimension-6);
}

.maps-property-section__head {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  margin-bottom: var(--dimension-4);
}

.maps-property-section__title {
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
