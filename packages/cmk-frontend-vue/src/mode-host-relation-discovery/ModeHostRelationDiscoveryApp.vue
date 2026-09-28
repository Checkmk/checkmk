<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBoxDeprecated from 'cmk-ui-library/components/CmkAlertBoxDeprecated.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkWizard, { CmkWizardButton, CmkWizardStep } from 'cmk-ui-library/components/CmkWizard'
import CmkProgressbar from 'cmk-ui-library/components/progress/CmkProgressbar.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import ConflictList from './ConflictList.vue'
import FindingList from './FindingList.vue'
import FindingReview from './FindingReview.vue'
import LabeledRow from './LabeledRow.vue'
import LookFor from './LookFor.vue'
import RunResult from './RunResult.vue'
import { acceptRelations, fetchStatus, startScan, suggestEvidence } from './api'
import { usePairNoun } from './relationWording'
import type {
  FindingRequest,
  FindingSummary,
  JobStatus,
  LookIn,
  RelationConflict,
  RelationGroup,
  RelationRow,
  RunSummary,
  ScanSummary,
  SharedValue,
  Suggestions,
  ValueChoice,
  WordChoice
} from './types'
import {
  acceptRequest,
  findingsToScan,
  isComplete,
  newValueChoice,
  noDecisions,
  partnersOf,
  relationsToStorePerFinding,
  valueKey,
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
const STEP_SUMMARY = 4
const POLL_INTERVAL_MS = 1000
/** How often in a row the status may not be read before the page gives up on the job. */
const POLL_ATTEMPTS = 5

const currentStep = ref(STEP_LOOK_FOR)

// Step 1: what to look for, and where. The names are where a fleet usually says it; the labels
// and attributes are asked for only when they are needed, since they find a lot to decide.
const kind = ref(Object.keys(props.kinds)[0] ?? '')
const lookIn = ref<LookIn[]>(['names'])
/** What the suggestions on hand were made for. */
const suggestedFor = ref('')
const wantedNow = computed(() => JSON.stringify([...lookIn.value].sort()))
const pairNounOf = usePairNoun(() => props.relation_nouns)

const indicators = computed(() =>
  [
    ...(lookIn.value.includes('names') ? [_t('Host names')] : []),
    ...(lookIn.value.includes('values') ? [_t('Host labels and custom host attributes')] : [])
  ].join(', ')
)
/** What step 1 said, for the step once it is done. */
const lookedFor = computed(() => [pairNounOf(kind.value), indicators.value].join(' · '))

// Step 2: what the findings mean.
const suggestions = ref<Suggestions | null>(null)
const suggesting = ref(false)
const suggestFailed = ref(false)
const ownWords = ref<string[]>([])
const ownValues = ref<SharedValue[]>([])
const wordChoices = ref<Record<string, WordChoice>>({})
const valueChoices = ref<Record<string, ValueChoice>>({})

// A finding ticked for one relation says nothing about another.
watch(kind, () => {
  wordChoices.value = {}
  valueChoices.value = {}
  suggestedFor.value = ''
})

const foundWords = computed(() => suggestions.value?.words ?? [])
const foundValues = computed(() => suggestions.value?.values ?? [])
const findings = computed(() =>
  findingsToScan(foundWords.value, wordChoices.value, foundValues.value, valueChoices.value)
)
const allComplete = computed(() =>
  foundValues.value.every((finding) =>
    isComplete(finding, valueChoices.value[valueKey(finding)] ?? newValueChoice(finding))
  )
)
const canScan = computed(() => findings.value.length > 0 && allComplete.value)
const nothingFound = computed(() => foundWords.value.length === 0 && foundValues.value.length === 0)

/** What each finding is called on the pages after the first, by its id. */
const findingTitles = computed<Record<string, string>>(() =>
  Object.fromEntries([
    ...foundWords.value.map(
      (finding) =>
        [wordFindingId(finding), _t('"%{word}" in the name', { word: finding.word })] as const
    ),
    ...foundValues.value.map(
      (finding) =>
        [
          valueKey(finding),
          finding.source === 'label'
            ? _t('Host label "%{name}"', { name: finding.name })
            : _t('Custom host attribute "%{name}"', { name: finding.name })
        ] as const
    )
  ])
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

/** How many relations the decisions store, per finding. */
const perFinding = computed(() =>
  scanned.value
    ? relationsToStorePerFinding(scanned.value.findings, decisions.value)
    : new Map<string, number>()
)
const toStore = computed(() =>
  [...perFinding.value.values()].reduce((count, relations) => count + relations, 0)
)
/** Whether a finding of the scan has anything the user could store - new relations or questions. */
function offersAnything(summary: FindingSummary): boolean {
  return (summary.counts.link ?? 0) > 0 || summary.questions > 0
}
const nothingNew = computed(
  () =>
    scanned.value !== null &&
    scanned.value.conflicts === 0 &&
    !scanned.value.findings.some(offersAnything)
)

/** Whether what step 2 says now is what the scan on hand was made for. */
const scanIsCurrent = computed(
  () =>
    scanned.value !== null && JSON.stringify(scannedFor.value) === JSON.stringify(findings.value)
)

/** The findings step 3 leaves anything to store of, by their titles. */
const storedFindings = computed(() =>
  (scanned.value?.findings ?? [])
    .filter((summary) => (perFinding.value.get(summary.id) ?? 0) > 0)
    .map((summary) => findingTitles.value[summary.id] ?? summary.id)
    .join(', ')
)

// Step 4: what is about to be stored, and then what the run did.
const runId = ref('')
const running = ref(false)
const runProgress = ref('')
const run = ref<RunSummary | null>(null)
const runText = ref('')
const runFailed = ref(false)

let unmounted = false

async function suggest(added: { word?: string } = {}): Promise<void> {
  suggesting.value = true
  const wanted = wantedNow.value
  try {
    const found = await suggestEvidence(ownWords.value, ownValues.value, lookIn.value)
    const next = withNewChoices(found, wordChoices.value, valueChoices.value, kind.value, added)
    wordChoices.value = next.words
    valueChoices.value = next.values
    suggestions.value = found
    suggestedFor.value = wanted
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

async function addValue(value: SharedValue): Promise<void> {
  if (!ownValues.value.some((own) => valueKey(own) === valueKey(value))) {
    ownValues.value = [...ownValues.value, value]
  }
  await suggest()
}

async function removeValue(value: SharedValue): Promise<void> {
  ownValues.value = ownValues.value.filter((own) => valueKey(own) !== valueKey(value))
  valueChoices.value = withoutKey(valueChoices.value, valueKey(value))
  await suggest()
}

/** Look through the hosts for what step 1 says, unless that is what is on hand already. */
async function suggestForStep1(): Promise<boolean> {
  if (lookIn.value.length === 0) {
    return false
  }
  if (suggestedFor.value !== wantedNow.value) {
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
      if (offersAnything(summary)) {
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

function answer(group: RelationGroup, host: string | null): void {
  if (host) {
    decisions.value.answers.set(group.key, {
      host,
      finding: group.finding,
      relations: partnersOf(group, host).length
    })
  } else {
    decisions.value.answers.delete(group.key)
  }
}

function resolve(conflict: RelationConflict, claim: RelationRow | null): void {
  if (claim) {
    decisions.value.resolutions.set(conflict.key, {
      claim: claim.key,
      finding: claim.finding,
      stores: claim.outcome === 'link'
    })
  } else {
    decisions.value.resolutions.delete(conflict.key)
  }
}

function nounOfFinding(findingId: string): string {
  const kind = scannedFor.value.find((finding) => finding.id === findingId)?.kind ?? ''
  return props.relation_nouns[props.kinds[kind] ?? ''] ?? ''
}

function resetRun(): void {
  run.value = null
  runText.value = ''
  runProgress.value = ''
  runFailed.value = false
}

async function store(): Promise<void> {
  running.value = true
  resetRun()
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
    resetRun()
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
          <CmkHeading type="h3">{{ _t('Relation mapping') }}</CmkHeading>
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
              v-model:look-in="lookIn"
              :kinds="props.kinds"
              :kind-words="props.kind_words"
              :relation-nouns="props.relation_nouns"
            />
            <div v-if="suggesting" class="mode-host-relation-discovery-app__running">
              <CmkProgressbar max="unknown" />
            </div>
            <CmkAlertBoxDeprecated v-else-if="suggestFailed" variant="error">
              {{ _t('The hosts could not be read.') }}
            </CmkAlertBoxDeprecated>
            <CmkParagraph
              v-else-if="lookIn.length === 0"
              class="mode-host-relation-discovery-app__dimmed"
            >
              {{ _t('To continue, say where Checkmk should look.') }}
            </CmkParagraph>
          </div>
        </template>
        <template #actions>
          <CmkWizardButton
            type="next"
            :override-label="suggesting ? _t('Looking through the hosts...') : _t('Continue')"
            :disabled="suggesting || lookIn.length === 0"
            :validation-cb="suggestForStep1"
          />
        </template>
      </CmkWizardStep>

      <CmkWizardStep :index="STEP_FOUND" :is-completed="() => currentStep > STEP_FOUND">
        <template #header>
          <CmkHeading type="h3">{{ _t('Relation proposal') }}</CmkHeading>
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
              v-model:value-choices="valueChoices"
              :words="foundWords"
              :values="foundValues"
              :label-names="suggestions.label_names"
              :attribute-names="suggestions.attribute_names"
              :kinds="props.kinds"
              :kind="kind"
              :look-in="lookIn"
              :relation-nouns="props.relation_nouns"
              :busy="suggesting"
              :own-words="ownWords"
              :own-values="ownValues.map(valueKey)"
              @add-word="addWord"
              @remove-word="removeWord"
              @add-value="addValue"
              @remove-value="removeValue"
            />
          </div>
          <CmkAlertBoxDeprecated v-if="suggestFailed || scanFailed" variant="error">
            {{ _t('The hosts could not be read.') }}
          </CmkAlertBoxDeprecated>
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
                ? _t('To continue, add what your hosts are related by.')
                : findings.length === 0
                  ? _t('To continue, tick at least one finding.')
                  : _t('To continue, answer the questions above.')
            }}
          </CmkParagraph>
        </template>
        <template #actions>
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
          <CmkWizardButton type="previous" :override-label="_t('Back')" />
        </template>
      </CmkWizardStep>

      <CmkWizardStep :index="STEP_CONFIRM" :is-completed="() => currentStep > STEP_CONFIRM">
        <template #header>
          <CmkHeading type="h3">{{ _t('Relation review') }}</CmkHeading>
        </template>
        <template #recap>
          <CmkParagraph class="mode-host-relation-discovery-app__dimmed">{{
            _tn('1 relation to store', '%{count} relations to store', toStore, { count: toStore })
          }}</CmkParagraph>
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
            <section
              v-if="scanned.conflicts > 0"
              class="mode-host-relation-discovery-app__attention"
            >
              <CmkHeading type="h4">
                {{
                  _tn(
                    'Needs your attention: 1 conflict',
                    'Needs your attention: %{count} conflicts',
                    scanned.conflicts,
                    { count: scanned.conflicts }
                  )
                }}
              </CmkHeading>
              <ConflictList
                :job-id="scanId"
                :relation-titles="props.relation_titles"
                :finding-titles="findingTitles"
                :resolutions="decisions.resolutions"
                @resolve="resolve"
              />
            </section>
            <FindingReview
              v-for="summary in scanned.findings"
              :key="`${scanId}:${summary.id}`"
              :job-id="scanId"
              :summary="summary"
              :title="findingTitles[summary.id] ?? summary.id"
              :noun="nounOfFinding(summary.id)"
              :folders="scanned.folders"
              :relation-titles="props.relation_titles"
              :relation-nouns="props.relation_nouns"
              :ticked="decisions.findings.has(summary.id)"
              :excluded="decisions.excluded"
              :answers="decisions.answers"
              @tick="(picked) => tick(summary.id, picked)"
              @toggle="toggle"
              @toggle-all="(keys, picked) => toggleAll(summary.id, keys, picked)"
              @answer="answer"
              @back="currentStep = STEP_FOUND"
            />
            <CmkParagraph v-if="toStore === 0" class="mode-host-relation-discovery-app__dimmed">
              {{
                nothingNew
                  ? _t(
                      'Nothing new was found: every relation is stored already or cannot be stored.'
                    )
                  : _t('To continue, choose at least one relation to store.')
              }}
            </CmkParagraph>
          </div>
        </template>
        <template #actions>
          <CmkWizardButton type="next" :override-label="_t('Continue')" :disabled="toStore === 0" />
          <CmkWizardButton type="previous" :override-label="_t('Back to the findings')" />
        </template>
      </CmkWizardStep>

      <CmkWizardStep :index="STEP_SUMMARY" :is-completed="() => run !== null">
        <template #header>
          <CmkHeading type="h3">{{ _t('Summary') }}</CmkHeading>
        </template>
        <template #content>
          <div class="mode-host-relation-discovery-app__summary">
            <LabeledRow :label="_t('Relation type')">{{ pairNounOf(kind) }}</LabeledRow>
            <LabeledRow :label="_t('Relation indicators')">{{ indicators }}</LabeledRow>
            <LabeledRow :label="_t('Findings')">{{ storedFindings }}</LabeledRow>
            <LabeledRow :label="_t('Relations to store')">{{ toStore }}</LabeledRow>
          </div>
          <div v-if="running" class="mode-host-relation-discovery-app__running">
            <CmkProgressbar max="unknown" />
            <CmkParagraph>{{ runProgress }}</CmkParagraph>
          </div>
          <CmkAlertBoxDeprecated v-else-if="runFailed" variant="error">
            {{ _t('The relations could not be stored.') }} {{ runText }}
          </CmkAlertBoxDeprecated>
          <RunResult
            v-else-if="run"
            :job-id="runId"
            :run="run"
            :summary="runText"
            :finding-titles="findingTitles"
            :relation-titles="props.relation_titles"
          />
          <!-- Scanning again starts here; it only moves on to the review once it has a scan. -->
          <CmkAlertBoxDeprecated v-if="scanFailed" variant="error">
            {{ _t('The hosts could not be read.') }}
          </CmkAlertBoxDeprecated>
        </template>
        <template #actions>
          <template v-if="!running">
            <!-- A run that failed may have lost its scan, so what is left is to scan again. -->
            <template v-if="run !== null || runFailed">
              <!-- What was stored does nothing until it is activated: the step a first-time user
                   must not miss, so it is the one that stands out. -->
              <CmkButton v-if="run !== null" variant="primary" :href="props.activate_changes_url">
                {{ _t('Activate changes') }}
              </CmkButton>
              <CmkWizardButton
                type="other"
                :override-label="scanning ? _t('Finding the relations...') : _t('Scan again')"
                :disabled="scanning"
                @click="scanAgain"
              />
            </template>
            <template v-else>
              <CmkWizardButton
                type="finish"
                :override-label="
                  _tn('Store 1 relation', 'Store %{count} relations', toStore, { count: toStore })
                "
                :disabled="toStore === 0"
                @click="store"
              />
              <CmkWizardButton type="previous" :override-label="_t('Back to the review')" />
            </template>
          </template>
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

.mode-host-relation-discovery-app__attention {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  padding: var(--spacing);
  border: 1px solid var(--ux-theme-4);
  border-radius: var(--border-radius);
}

.mode-host-relation-discovery-app__summary {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-half);
  margin-bottom: var(--spacing);
}

.mode-host-relation-discovery-app__running {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-half);
}
</style>
