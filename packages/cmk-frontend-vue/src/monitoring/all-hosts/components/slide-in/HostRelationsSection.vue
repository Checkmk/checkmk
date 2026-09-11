<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkLinkCard from 'cmk-ui-library/components/CmkLinkCard'
import StateTag from 'cmk-ui-library/components/StateTag.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, nextTick, ref, useTemplateRef, watch } from 'vue'

import type { HostOverview, HostRef } from '@/monitoring/shared/api/types'
import HostStateDisplay from '@/monitoring/shared/components/HostStateDisplay.vue'
import ServiceSummaryBar from '@/monitoring/shared/components/ServiceSummaryBar.vue'

type Relation = HostOverview['relations'][number]

const props = withDefaults(
  defineProps<{
    relations: HostOverview['relations']
    /** Whether the server left relations out of the list entirely. */
    moreRelations?: boolean
    /** Counts how often the reader asked for the relations; 0 means they did not. */
    revealRequest?: number
  }>(),
  { moreRelations: false, revealRequest: 0 }
)

const { _t, _tn } = usei18n()

/** How many related hosts are listed before the reader has to ask for the rest. */
const RELATION_PREVIEW_LIMIT = 5

// The list is cut server-side, so it names how many made it rather than how many were left out.
const truncationNotice = computed(() =>
  _t('This host is related to more hosts than the %{count} listed here.', {
    count: props.relations.length
  })
)

const shownInFull = ref(false)

const shownRelations = computed<Relation[]>(() =>
  shownInFull.value ? props.relations : props.relations.slice(0, RELATION_PREVIEW_LIMIT)
)

const showMoreLabel = computed<TranslatedString>(() => {
  if (shownInFull.value) {
    return _t('Show fewer')
  }
  const hidden = props.relations.length - RELATION_PREVIEW_LIMIT
  return _tn('Show 1 more host', 'Show %{count} more hosts', hidden, { count: hidden })
})

// A relation whose host is simply gone is not listed at all, so a card without health always
// means the same thing: its site did not answer.
function siteUnavailableNotice(relation: Relation): TranslatedString {
  return _t('Site %{site} is not available, so the state of this host cannot be read.', {
    site: relation.site_id
  })
}

// A name is only unique together with the site it is monitored on, and one host can be named by
// two relations of different kinds or by both ends of one.
function relationKey(relation: Relation): string {
  return `${relation.site_id}/${relation.host_name}/${relation.kind}/${relation.direction}`
}

function hostRef(relation: Relation): HostRef {
  return { site_id: relation.site_id, name: relation.host_name }
}

const section = useTemplateRef<HTMLElement>('section')

// Watched rather than done on mount: the panel keeps the same tab when the reader clicks the
// relation count of the host it already shows, so there is no second mount to hang this on.
watch(
  () => props.revealRequest,
  async (request) => {
    if (!request) {
      return
    }
    await nextTick()
    // Focused rather than scrolled: the dialog puts the reading cursor at the top of the panel,
    // and focus() takes it along instead of only moving pixels.
    section.value?.focus()
  },
  { immediate: true }
)
</script>

<template>
  <section ref="section" tabindex="-1" class="monitoring-host-relations-section">
    <CmkHeading type="h3">{{ _t('Relations') }}</CmkHeading>
    <CmkParagraph v-if="relations.length === 0" class="monitoring-host-relations-section__empty">
      {{ _t('No relations set') }}
    </CmkParagraph>
    <template v-else>
      <ul
        id="monitoring-host-relations-section-list"
        class="monitoring-host-relations-section__list"
      >
        <li v-for="relation in shownRelations" :key="relationKey(relation)">
          <CmkLinkCard
            borders="borderless"
            contrast="high"
            :title="untranslated(relation.host_name)"
            :subtitle="_t('Relation type: %{type}', { type: relation.relation_type })"
            :open-in-new-tab="false"
          >
            <template #leading>
              <HostStateDisplay
                v-if="relation.health"
                :state="relation.health.state"
                class="monitoring-host-relations-section__state"
              />
              <StateTag
                v-else
                kind="host"
                tone="unknown"
                :label="_t('UNKNOWN')"
                class="monitoring-host-relations-section__state"
              />
            </template>
            <ServiceSummaryBar
              v-if="relation.health"
              :counts="relation.health.service_counts"
              :host="hostRef(relation)"
              size="small"
            />
            <CmkParagraph v-else class="monitoring-host-relations-section__unavailable">
              {{ siteUnavailableNotice(relation) }}
            </CmkParagraph>
          </CmkLinkCard>
        </li>
      </ul>
      <CmkButton
        v-if="relations.length > RELATION_PREVIEW_LIMIT"
        variant="optional"
        size="small"
        class="monitoring-host-relations-section__more"
        :aria-expanded="shownInFull"
        aria-controls="monitoring-host-relations-section-list"
        @click="shownInFull = !shownInFull"
      >
        {{ showMoreLabel }}
      </CmkButton>
      <CmkAlertBox v-if="moreRelations" variant="info" size="small">
        {{ truncationNotice }}
      </CmkAlertBox>
    </template>
  </section>
</template>

<style scoped>
.monitoring-host-relations-section {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.monitoring-host-relations-section__empty,
.monitoring-host-relations-section__unavailable {
  color: var(--font-color-dimmed);
}

.monitoring-host-relations-section__list {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  padding: 0;
  margin: 0;
  list-style: none;
}

/* The card centres what it leads with, but the state belongs next to the host name. */
.monitoring-host-relations-section__state {
  flex: 0 0 auto;
  align-self: flex-start;
  margin-right: var(--dimension-6);
}

.monitoring-host-relations-section__more {
  align-self: flex-start;
}
</style>
