<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import { CmkRadioButton, CmkRadioGroup } from 'cmk-ui-library/components/user-input/CmkRadioButton'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import useId from 'cmk-ui-library/lib/useId'

import RowPager from './RowPager.vue'
import type { RelationConflict, RelationRow } from './types'
import usePagedRows from './usePagedRows'

const PAGE_SIZE = 20

const { _t } = usei18n()

/** What a radio button stands for when the user wants neither claim stored. */
const NEITHER = ''

const props = defineProps<{
  jobId: string
  relationTitles: Record<string, string>
  /** What the finding of each claim is called, by finding id. */
  findingTitles: Record<string, string>
  /** The claim picked per conflict so far, by conflict key. */
  resolutions: ReadonlyMap<string, { claim: string }>
}>()

const emit = defineEmits<{
  resolve: [conflict: RelationConflict, claim: RelationRow | null]
}>()

const idPrefix = useId()

const { page, offset, failed } = usePagedRows(
  () => props.jobId,
  () => ({ part: 'conflicts' }),
  PAGE_SIZE
)

function claimLabel(claim: RelationRow): TranslatedString {
  return _t('%{source} %{relation} %{target} (%{finding})', {
    source: claim.source_host,
    relation: props.relationTitles[claim.relation] ?? claim.relation,
    target: claim.target_host,
    finding: props.findingTitles[claim.finding] ?? claim.finding
  })
}

function resolve(conflict: RelationConflict, picked: string): void {
  emit('resolve', conflict, conflict.claims.find((claim) => claim.key === picked) ?? null)
}
</script>

<template>
  <div class="mode-host-relation-discovery-conflict-list">
    <CmkAlertBox v-if="failed" variant="error" size="small">
      {{ _t('The conflicts could not be read.') }}
    </CmkAlertBox>
    <ul v-else-if="page" class="mode-host-relation-discovery-conflict-list__list">
      <li
        v-for="conflict in page.conflicts"
        :key="conflict.key"
        class="mode-host-relation-discovery-conflict-list__conflict"
      >
        <CmkParagraph :id="`${idPrefix}-${conflict.key}`">
          {{
            _t('Your hosts say different things about %{first} and %{second}:', {
              first: conflict.hosts[0] ?? '',
              second: conflict.hosts[1] ?? ''
            })
          }}
        </CmkParagraph>
        <CmkRadioGroup
          :model-value="props.resolutions.get(conflict.key)?.claim ?? NEITHER"
          :aria-labelledby="`${idPrefix}-${conflict.key}`"
          @update:model-value="(picked: string) => resolve(conflict, picked)"
        >
          <CmkRadioButton
            v-for="claim in conflict.claims"
            :key="claim.key"
            :value="claim.key"
            :label="claimLabel(claim)"
          />
          <CmkRadioButton :value="NEITHER" :label="_t('Neither - store nothing for these two')" />
        </CmkRadioGroup>
      </li>
    </ul>
    <RowPager v-if="page" v-model:offset="offset" :total="page.total" :page-size="PAGE_SIZE" />
  </div>
</template>

<style scoped>
.mode-host-relation-discovery-conflict-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

.mode-host-relation-discovery-conflict-list__list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  margin: 0;
  padding: 0;
  list-style: none;
}

.mode-host-relation-discovery-conflict-list__conflict {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-half);
}
</style>
