<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkWizard, { CmkWizardButton, CmkWizardStep } from 'cmk-ui-library/components/CmkWizard'
import CmkProgressbar from 'cmk-ui-library/components/progress/CmkProgressbar.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import FindingList from './FindingList.vue'
import FindingReview from './FindingReview.vue'
import LookFor from './LookFor.vue'
import RunResult from './RunResult.vue'
import { acceptRelations, fetchStatus, startScan, suggestEvidence } from './api'
import { usePairNoun } from './relationWording'
import type {
  FindingRequest,
  JobStatus,
  RelationRow,
  RunSummary,
  ScanSummary,
  Suggestions,
  WordChoice
} from './types'
import {
  acceptRequest,
  findingsToScan,
  noDecisions,
  relationsToStore,
  withNewChoices,
  withoutKey,
  wordFindingId
} from './types'

const { _t, _tn } = usei18n()

/**
 * Spelled out rather than derived from HostRelationDiscovery: the SFC compiler resolves
 * the props type on its own and cannot follow mapped types such as Omit or Record here.
 */
interface Props {
  kinds: Record<string, string>
  kind_words: Record<string, string[]>
  relation_titles: Record<string, string>
  relation_nouns: Record<string, string>
  activate_changes_url: string
}

const props = defineProps<Props>()

const STEP_LOOK_FOR = 1
const STEP_FOUND = 2
const STEP_CONFIRM = 3
const STEP_RESULT = 4
const POLL_INTERVAL_MS = 1000
/** How often in a row the status may not be read before the page gives up on the job. */
const POLL_ATTEMPTS = 5

const currentStep = ref(STEP_LOOK_FOR)

// Step 1: what to look for. The host names are where a fleet usually says it.
const kind = ref(Object.keys(props.kinds)[0] ?? '')
/** Whether the suggestions on hand are the ones for what step 1 says. */
const lookedThrough = ref(false)
const pairNounOf = usePairNoun(() => props.relation_nouns)

/** What step 1 said, for the step once it is done. */
const lookedFor = computed(() =>
  _t('%{relation}, %{where}', { relation: pairNounOf(kind.value), where: _t('in the host names') })
)

// Step 2: what the findings mean.
const suggestions = ref<Suggestions | null>(null)
const suggesting = ref(false)
const suggestFailed = ref(false)
const ownWords = ref<string[]>([])
const wordChoices = ref<Record<string, WordChoice>>({})

// A finding ticked for one relation says nothing about another.
watch(kind, () => {
  wordChoices.value = {}
  lookedThrough.value = false
})

const foundWords = computed(() => suggestions.value?.words ?? [])
const findings = computed(() => findingsToScan(foundWords.value, wordChoices.value))
const canScan = computed(() => findings.value.length > 0)
const nothingFound = computed(() => foundWords.value.length === 0)

/** What each finding is called on the pages after the first, by its id. */
const findingTitles = computed<Record<string, string>>(() =>
  Object.fromEntries(
    foundWords.value.map(
      (finding) =>
        [wordFindingId(finding), _t('"%{word}" in the name', { word: finding.word })] as const
    )
  )
)

/** What step 2 said, for the step once it is done. */
const ticked = computed(() =>
  findings.value.map((finding) => findingTitles.value[finding.id] ?? finding.id).join(', ')
)

// Step 3: what of the scan to store.
const scanId = ref('')
const scanned = ref<ScanSummary | null>(null)
const scannedFor = ref<FindingRequest[]>([])
const scanning = ref(false)
const scanFailed = ref(false)
const scanProgress = ref('')
const decisions = ref(noDecisions())

const toStore = computed(() =>
  scanned.value ? relationsToStore(scanned.value.findings, decisions.value) : 0
)
/** Whether what step 2 says now is what the scan on hand was made for. */
const scanIsCurrent = computed(
  () =>
    scanned.value !== null && JSON.stringify(scannedFor.value) === JSON.stringify(findings.value)
)

// Step 4: what the run did.
const runId = ref('')
const running = ref(false)
const runProgress = ref('')
const run = ref<RunSummary | null>(null)
const runText = ref('')
const runFailed = ref(false)

let unmounted = false

async function suggest(added: { word?: string } = {}): Promise<void> {
  suggesting.value = true
  try {
    const found = await suggestEvidence(ownWords.value)
    wordChoices.value = withNewChoices(found, wordChoices.value, kind.value, added)
    suggestions.value = found
    lookedThrough.value = true
    suggestFailed.value = false
  } catch {
    suggestFailed.value = true
  } finally {
    suggesting.value = false
  }
}

async function addWord(word: string): Promise<void> {
  if (!ownWords.value.includes(word)) {
    ownWords.value = [...ownWords.value, word]
  }
  await suggest({ word })
}

async function removeWord(word: string): Promise<void> {
  ownWords.value = ownWords.value.filter((own) => own !== word)
  wordChoices.value = withoutKey(wordChoices.value, word)
  await suggest()
}

/** Look through the hosts for what step 1 says, unless that is what is on hand already. */
async function suggestForStep1(): Promise<boolean> {
  if (!lookedThrough.value) {
    await suggest()
  }
  return !suggestFailed.value && suggestions.value !== null
}

onBeforeUnmount(() => {
  unmounted = true
})

function pause(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS))
}

/** The job's status once it has finished, reporting its progress on the way. */
async function finished(jobId: string, progress: (message: string) => void): Promise<JobStatus> {
  let failures = 0
  for (;;) {
    if (unmounted) {
      throw new Error('The page was left.')
    }
    try {
      const status = await fetchStatus(jobId)
      failures = 0
      if (!status.running) {
        return status
      }
      progress(status.message)
    } catch (error) {
      failures += 1
      if (failures >= POLL_ATTEMPTS) {
        throw error
      }
    }
    await pause()
  }
}

/**
 * Scan for what step 2 says. Answers whether step 3 can be shown. Everything that can be
 * stored starts out chosen, the way the service discovery offers what it found: taking out
 * the few that are wrong is less work than picking the many that are right.
 */
async function scan(asked: FindingRequest[] = findings.value): Promise<boolean> {
  scanning.value = true
  scanProgress.value = ''
  try {
    const jobId = await startScan(asked)
    const status = await finished(jobId, (message) => (scanProgress.value = message))
    if (status.scan === null) {
      throw new Error(status.summary)
    }
    scanId.value = jobId
    scanned.value = status.scan
    scannedFor.value = asked
    decisions.value = noDecisions()
    for (const summary of status.scan.findings) {
      if ((summary.counts.link ?? 0) > 0) {
        decisions.value.findings.add(summary.id)
      }
    }
    scanFailed.value = false
    return true
  } catch {
    scanFailed.value = true
    return false
  } finally {
    scanning.value = false
  }
}

async function scanForStep2(): Promise<boolean> {
  return canScan.value && (scanIsCurrent.value || (await scan()))
}

function tick(finding: string, picked: boolean): void {
  if (picked) {
    decisions.value.findings.add(finding)
  } else {
    decisions.value.findings.delete(finding)
  }
}

function toggle(row: RelationRow, picked: boolean): void {
  if (picked) {
    decisions.value.excluded.delete(row.key)
  } else {
    decisions.value.excluded.set(row.key, row.finding)
  }
}

function toggleAll(finding: string, keys: string[], picked: boolean): void {
  for (const key of keys) {
    if (picked) {
      decisions.value.excluded.delete(key)
    } else {
      decisions.value.excluded.set(key, finding)
    }
  }
}

async function store(): Promise<void> {
  running.value = true
  runFailed.value = false
  runProgress.value = ''
  runText.value = ''
  run.value = null
  currentStep.value = STEP_RESULT
  try {
    runId.value = await acceptRelations(acceptRequest(scanId.value, decisions.value))
    const status = await finished(runId.value, (message) => (runProgress.value = message))
    runText.value = status.summary
    if (status.run === null) {
      throw new Error(status.summary)
    }
    run.value = status.run
  } catch {
    runFailed.value = true
  } finally {
    running.value = false
  }
}

/** Back to deciding: read the hosts once more, with what step 2 said last time. */
async function scanAgain(): Promise<void> {
  if (await scan(scannedFor.value)) {
    currentStep.value = STEP_CONFIRM
  }
}
</script>

<template>
  <div class="mode-host-relation-discovery-app">
    <CmkParagraph>
      {{
        _t(
          'Related hosts are shown together in the monitoring - a server and its management board, for example. Checkmk looks for them in all hosts in Setup. Nothing is changed until you store.'
        )
      }}
    </CmkParagraph>
    <CmkWizard v-model="currentStep" mode="guided" :locked="running || scanning || suggesting">
      <CmkWizardStep :index="STEP_LOOK_FOR" :is-completed="() => currentStep > STEP_LOOK_FOR">
        <template #header>
          <CmkHeading type="h3">{{ _t('What to look for') }}</CmkHeading>
        </template>
        <template #recap>
          <CmkParagraph class="mode-host-relation-discovery-app__dimmed">{{
            lookedFor
          }}</CmkParagraph>
        </template>
        <template #content>
          <div class="mode-host-relation-discovery-app__step">
            <LookFor
              v-model:kind="kind"
              :kinds="props.kinds"
              :kind-words="props.kind_words"
              :relation-nouns="props.relation_nouns"
            />
            <div v-if="suggesting" class="mode-host-relation-discovery-app__running">
              <CmkProgressbar max="unknown" />
            </div>
            <CmkAlertBox v-else-if="suggestFailed" variant="error">
              {{ _t('The hosts could not be read.') }}
            </CmkAlertBox>
          </div>
        </template>
        <template #actions>
          <CmkWizardButton
            type="next"
            :override-label="suggesting ? _t('Looking through the hosts...') : _t('Continue')"
            :disabled="suggesting"
            :validation-cb="suggestForStep1"
          />
        </template>
      </CmkWizardStep>

      <CmkWizardStep :index="STEP_FOUND" :is-completed="() => currentStep > STEP_FOUND">
        <template #header>
          <CmkHeading type="h3">{{ _t('What Checkmk found in your hosts') }}</CmkHeading>
        </template>
        <template #recap>
          <CmkParagraph class="mode-host-relation-discovery-app__dimmed">{{ ticked }}</CmkParagraph>
        </template>
        <template #content>
          <div v-if="suggestions !== null" class="mode-host-relation-discovery-app__step">
            <CmkParagraph class="mode-host-relation-discovery-app__dimmed">
              {{
                _tn(
                  'Checkmk read 1 host.',
                  'Checkmk read %{count} hosts.',
                  suggestions.hosts_scanned,
                  {
                    count: suggestions.hosts_scanned
                  }
                )
              }}
            </CmkParagraph>
            <FindingList
              v-model:word-choices="wordChoices"
              :words="foundWords"
              :kinds="props.kinds"
              :kind="kind"
              :relation-nouns="props.relation_nouns"
              :busy="suggesting"
              :own-words="ownWords"
              @add-word="addWord"
              @remove-word="removeWord"
            />
          </div>
          <CmkAlertBox v-if="suggestFailed || scanFailed" variant="error">
            {{ _t('The hosts could not be read.') }}
          </CmkAlertBox>
          <div v-if="scanning" class="mode-host-relation-discovery-app__running">
            <CmkProgressbar max="unknown" />
            <CmkParagraph>{{ scanProgress }}</CmkParagraph>
          </div>
          <CmkParagraph
            v-else-if="suggestions !== null && !canScan"
            class="mode-host-relation-discovery-app__dimmed"
          >
            {{
              nothingFound
                ? _t('To continue, add a word your host names use.')
                : _t('To continue, tick at least one finding.')
            }}
          </CmkParagraph>
        </template>
        <template #actions>
          <CmkWizardButton type="previous" :override-label="_t('Back')" />
          <CmkWizardButton
            type="next"
            :override-label="
              scanning
                ? _t('Finding the relations...')
                : scanIsCurrent
                  ? _t('Back to what was found')
                  : _t('Continue')
            "
            :disabled="scanning || !canScan"
            :validation-cb="scanForStep2"
          />
        </template>
      </CmkWizardStep>

      <CmkWizardStep :index="STEP_CONFIRM" :is-completed="() => currentStep > STEP_CONFIRM">
        <template #header>
          <CmkHeading type="h3">{{ _t('Check what will be stored') }}</CmkHeading>
        </template>
        <template #content>
          <div v-if="scanned" class="mode-host-relation-discovery-app__step">
            <CmkParagraph class="mode-host-relation-discovery-app__dimmed">
              {{
                _tn(
                  '1 host read. Every finding you tick is stored as a whole; untick single relations below if they are wrong.',
                  '%{count} hosts read. Every finding you tick is stored as a whole; untick single relations below if they are wrong.',
                  scanned.hosts_scanned,
                  { count: scanned.hosts_scanned }
                )
              }}
            </CmkParagraph>
            <FindingReview
              v-for="summary in scanned.findings"
              :key="`${scanId}:${summary.id}`"
              :job-id="scanId"
              :summary="summary"
              :title="findingTitles[summary.id] ?? summary.id"
              :folders="scanned.folders"
              :relation-titles="props.relation_titles"
              :ticked="decisions.findings.has(summary.id)"
              :excluded="decisions.excluded"
              @tick="(picked) => tick(summary.id, picked)"
              @toggle="toggle"
              @toggle-all="(keys, picked) => toggleAll(summary.id, keys, picked)"
            />
          </div>
        </template>
        <template #actions>
          <CmkWizardButton type="previous" :override-label="_t('Back to the findings')" />
          <CmkWizardButton
            type="finish"
            :override-label="
              _tn('Store 1 relation', 'Store %{count} relations', toStore, { count: toStore })
            "
            :disabled="toStore === 0"
            @click="store"
          />
        </template>
      </CmkWizardStep>

      <CmkWizardStep :index="STEP_RESULT" :is-completed="() => run !== null">
        <template #header>
          <CmkHeading type="h3">{{ _t('Result') }}</CmkHeading>
        </template>
        <template #content>
          <div v-if="running" class="mode-host-relation-discovery-app__running">
            <CmkProgressbar max="unknown" />
            <CmkParagraph>{{ runProgress }}</CmkParagraph>
          </div>
          <CmkAlertBox v-else-if="runFailed" variant="error">
            {{ _t('The relations could not be stored.') }} {{ runText }}
          </CmkAlertBox>
          <RunResult
            v-else-if="run"
            :job-id="runId"
            :run="run"
            :summary="runText"
            :finding-titles="findingTitles"
            :relation-titles="props.relation_titles"
          />
        </template>
        <template #actions>
          <!-- What was stored does nothing until it is activated: the step a first-time user
               must not miss, so it is the one that stands out. -->
          <CmkButton v-if="run" variant="primary" :href="props.activate_changes_url">
            {{ _t('Activate changes') }}
          </CmkButton>
          <CmkWizardButton
            v-if="!running"
            type="other"
            :override-label="scanning ? _t('Finding the relations...') : _t('Scan again')"
            :disabled="scanning"
            @click="scanAgain"
          />
        </template>
      </CmkWizardStep>
    </CmkWizard>
  </div>
</template>

<style scoped>
.mode-host-relation-discovery-app {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  max-width: 1200px;
}

.mode-host-relation-discovery-app__dimmed {
  color: var(--font-color-dimmed);
}

/* The buttons of a step name a count or an action in two words; neither must wrap.
   Reaching into the wizard's own class is the only way to say so from here. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.mode-host-relation-discovery-app :deep(.cmk-wizard-step__actions button) {
  white-space: nowrap;
}

.mode-host-relation-discovery-app__step {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

.mode-host-relation-discovery-app__running {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-half);
}
</style>
