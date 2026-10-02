<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBoxDeprecated from 'cmk-ui-library/components/CmkAlertBoxDeprecated.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import PagedRelations from './PagedRelations.vue'
import { countedOutcomes } from './outcomes'
import type { RunSummary } from './types'

const { _t } = usei18n()

const props = defineProps<{
  jobId: string
  run: RunSummary
  summary: string
  findingTitles: Record<string, string>
  relationTitles: Record<string, string>
}>()

const NOTHING_EXCLUDED: ReadonlyMap<string, string> = new Map()
</script>

<template>
  <div class="mode-host-relation-detection-run-result">
    <CmkAlertBoxDeprecated :variant="props.run.failed > 0 ? 'warning' : 'success'" size="small">
      {{ props.summary }}
    </CmkAlertBoxDeprecated>
    <ul class="mode-host-relation-detection-run-result__findings">
      <li
        v-for="finding in props.run.findings.filter((f) => countedOutcomes(f.counts) !== '')"
        :key="finding.id"
      >
        <span class="mode-host-relation-detection-run-result__title">{{
          props.findingTitles[finding.id] ?? finding.id
        }}</span>
        &ensp;<span class="mode-host-relation-detection-run-result__counts">{{
          countedOutcomes(finding.counts, true)
        }}</span>
      </li>
    </ul>
    <template v-if="props.run.failed > 0">
      <CmkHeading type="h4">{{ _t('What could not be stored') }}</CmkHeading>
      <CmkParagraph>
        {{
          _t(
            'Fix these in the properties of the hosts, or in the folders they are in, and scan again.'
          )
        }}
      </CmkParagraph>
      <PagedRelations
        :job-id="props.jobId"
        part="failed"
        :folders="[]"
        :relation-titles="props.relationTitles"
        :selectable="false"
        :excluded="NOTHING_EXCLUDED"
      />
    </template>
  </div>
</template>

<style scoped>
.mode-host-relation-detection-run-result {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

.mode-host-relation-detection-run-result__findings {
  margin: 0;
  padding: 0;
  list-style: none;
}

.mode-host-relation-detection-run-result__title {
  font-weight: var(--font-weight-bold);
}

.mode-host-relation-detection-run-result__counts {
  color: var(--font-color-dimmed);
}
</style>
