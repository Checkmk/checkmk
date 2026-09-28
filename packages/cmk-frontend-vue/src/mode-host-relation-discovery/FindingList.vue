<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkCollapsible, { CmkCollapsibleTitle } from 'cmk-ui-library/components/CmkCollapsible'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import type { Suggestions as DropdownOptions } from 'cmk-ui-library/components/CmkSuggestions'
import CmkTag from 'cmk-ui-library/components/CmkTag.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInlineButton from 'cmk-ui-library/components/user-input/CmkInlineButton.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import { CmkRadioButton, CmkRadioGroup } from 'cmk-ui-library/components/user-input/CmkRadioButton'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import useId from 'cmk-ui-library/lib/useId'
import { computed, ref } from 'vue'

import type {
  LookIn,
  SharedValue,
  ValueChoice,
  ValueFinding,
  WordChoice,
  WordFinding
} from './types'
import {
  NOT_RELATED,
  isComplete,
  isMarkedByValue,
  isMarker,
  isNameWord,
  newValueChoice,
  resolvedMarker,
  valueKey,
  wordsOf
} from './types'

const { _t, _tn } = usei18n()

const props = defineProps<{
  words: WordFinding[]
  values: ValueFinding[]
  labelNames: string[]
  attributeNames: string[]
  /** Per kind of relation, the end a finding marks, by the name the wire uses for it. */
  kinds: Record<string, string>
  /** The kind the user looks for: what every finding ticked here stands for. */
  kind: string
  lookIn: LookIn[]
  relationNouns: Record<string, string>
  ownWords: string[]
  ownValues: string[]
  busy: boolean
}>()

const emit = defineEmits<{
  addWord: [word: string]
  removeWord: [word: string]
  addValue: [value: SharedValue]
  removeValue: [value: SharedValue]
}>()

const wordChoices = defineModel<Record<string, WordChoice>>('wordChoices', { required: true })
const valueChoices = defineModel<Record<string, ValueChoice>>('valueChoices', { required: true })

const newWordId = useId()
const idPrefix = useId()
const newWord = ref('')
const newWordErrors = ref<string[]>([])
const addingOpen = ref(false)
/** What the user added last, to say next to the field where it went. */
const added = ref('')
const addValueId = useId()

/** How many hosts of a shared value an example names: a chassis has dozens, a category hundreds. */
const EXAMPLE_HOSTS = 4

const inNames = computed(() => props.lookIn.includes('names'))
const inValues = computed(() => props.lookIn.includes('values'))
const nothingFound = computed(() => props.words.length === 0 && props.values.length === 0)

/** What the host a finding marks is called: "Management board". */
function nounOf(kind: string): string {
  return props.relationNouns[props.kinds[kind] ?? ''] ?? kind
}

/** What the host at the other end is called: "OS host". */
const otherNoun = computed(() => {
  const marked = props.kinds[props.kind] ?? ''
  const other = marked.endsWith('_parent')
    ? `${props.kind}_child`
    : marked.endsWith('_child')
      ? `${props.kind}_parent`
      : marked
  return props.relationNouns[other] ?? ''
})

const noun = computed(() => nounOf(props.kind))

/** The words the user gave this relation, for a value finding to mark its ends by. */
const kindWords = computed(() => wordsOf(props.kind, props.words, wordChoices.value))

function named(names: string[]) {
  return names.map((name) => ({ name, title: untranslated(name) }))
}

const labelOptions = computed<DropdownOptions>(() => ({
  type: 'filtered',
  suggestions: named(props.labelNames)
}))

const attributeOptions = computed<DropdownOptions>(() => ({
  type: 'filtered',
  suggestions: named(props.attributeNames)
}))

/**
 * What a user can still add as a shared value, keyed the way the findings are: neither one
 * already on the page nor one of Checkmk's own labels, which are never a serial number.
 */
const addableValues = computed(() => {
  const listed = new Set(props.values.map(valueKey))
  const candidates: SharedValue[] = [
    ...props.labelNames
      .filter((name) => !name.startsWith('cmk/'))
      .map((name) => ({ source: 'label' as const, name })),
    ...props.attributeNames.map((name) => ({ source: 'attribute' as const, name }))
  ]
  return new Map(
    candidates
      .filter((value) => !listed.has(valueKey(value)))
      .map((value) => [valueKey(value), value] as const)
  )
})

const sharedValueOptions = computed<DropdownOptions>(() => {
  const addable = [...addableValues.value.values()]
  return {
    type: 'filtered',
    suggestions: [
      {
        title: _t('Host labels'),
        suggestions: addable
          .filter((value) => value.source === 'label')
          .map((value) => ({ name: valueKey(value), title: untranslated(value.name) }))
      },
      {
        title: _t('Custom host attributes'),
        suggestions: addable
          .filter((value) => value.source === 'attribute')
          .map((value) => ({ name: valueKey(value), title: untranslated(value.name) }))
      }
    ].filter((section) => section.suggestions.length > 0)
  }
})

function wordTitle(finding: WordFinding): TranslatedString {
  if (finding.pairs === 0) {
    return _t('No host is named like another host plus "%{word}"', { word: finding.word })
  }
  return _tn(
    '%{count} host is named like another host plus "%{word}"',
    '%{count} hosts are named like another host plus "%{word}"',
    finding.pairs,
    { count: finding.pairs, word: finding.word }
  )
}

/** Counted the way the word findings are - by what would be related - rather than by value. */
function valueTitle(finding: ValueFinding): TranslatedString {
  const what =
    finding.source === 'label'
      ? _t('host label "%{name}"', { name: finding.name })
      : _t('custom host attribute "%{name}"', { name: finding.name })
  if (finding.groups === 0) {
    return finding.too_wide > 0
      ? _t('Every value of the %{what} is shared by too many hosts to pair them', { what })
      : _t('No two hosts share a value in the %{what}', { what })
  }
  return finding.largest_group === 2
    ? _tn(
        '1 pair of hosts shares a value in the %{what}',
        '%{count} pairs of hosts share a value in the %{what}',
        finding.groups,
        { count: finding.groups, what }
      )
    : _tn(
        '1 group of hosts shares a value in the %{what}',
        '%{count} groups of hosts share a value in the %{what}',
        finding.groups,
        { count: finding.groups, what }
      )
}

function removeWordTitle(finding: WordFinding): TranslatedString {
  return _t('Remove the word "%{word}"', { word: finding.word })
}

function removeValueTitle(finding: ValueFinding): TranslatedString {
  return _t('Remove "%{name}"', { name: finding.name })
}

function moreThanShown(count: number): TranslatedString {
  return _tn('and 1 more', 'and %{count} more', count, { count })
}

/** The shared value the way Checkmk shows a label everywhere else: "cmdb/sn:S-1". */
function valueTag(name: string, value: string): TranslatedString {
  return untranslated(`${name}:${value}`)
}

/** The words the kind looked for declares, then what only the user can say anything about. */
const knownWords = computed(() =>
  props.words.filter((finding) => finding.kind === props.kind && finding.pairs > 0)
)
const otherWords = computed(() =>
  props.words.filter((finding) => finding.kind !== props.kind || finding.pairs === 0)
)

function wordChoice(finding: WordFinding): WordChoice {
  return wordChoices.value[finding.word] ?? { meaning: finding.kind ?? NOT_RELATED }
}

function valueChoice(finding: ValueFinding): ValueChoice {
  return valueChoices.value[valueKey(finding)] ?? newValueChoice(finding)
}

function isWordMeant(finding: WordFinding): boolean {
  return finding.pairs > 0 && wordChoice(finding).meaning === props.kind
}

function setWordMeant(finding: WordFinding, meant: boolean): void {
  wordChoices.value = {
    ...wordChoices.value,
    [finding.word]: { meaning: meant ? props.kind : NOT_RELATED }
  }
}

function isValueMeant(finding: ValueFinding): boolean {
  return finding.groups > 0 && valueChoice(finding).meaning === props.kind
}

function updateValue(finding: ValueFinding, patch: Partial<ValueChoice>): void {
  valueChoices.value = {
    ...valueChoices.value,
    [valueKey(finding)]: { ...valueChoice(finding), ...patch }
  }
}

function updateMarker(finding: ValueFinding, marker: string): void {
  if (isMarker(marker)) {
    const choice = valueChoice(finding)
    updateValue(finding, {
      marker,
      // The detected value is the one to start from again, and a value of its own starts empty.
      markValue: marker === 'detected' ? (finding.told_apart?.suggested ?? '') : '',
      markName: marker === choice.marker ? choice.markName : ''
    })
  }
}

/** The values that stand alone in their group, to pick the one the deciding end carries. */
function detectedValues(finding: ValueFinding): DropdownOptions {
  return {
    type: 'fixed',
    suggestions: (finding.told_apart?.values ?? []).map((counted) => ({
      name: counted.value,
      title: _tn('%{value} (in 1 group)', '%{value} (in %{count} groups)', counted.groups, {
        value: counted.value,
        count: counted.groups
      })
    }))
  }
}

/** Why some of a value's hosts are left out: a value on that many hosts is a category. */
function tooWide(finding: ValueFinding): TranslatedString {
  return _tn(
    '1 value is shared by so many hosts that it names a kind of host rather than one machine. Its hosts are left out.',
    '%{count} values are each shared by so many hosts that they name kinds of hosts rather than one machine. Their hosts are left out.',
    finding.too_wide,
    { count: finding.too_wide }
  )
}

function exampleHosts(hosts: string[]): string {
  return hosts.length > EXAMPLE_HOSTS
    ? _tn('%{hosts} and 1 more', '%{hosts} and %{count} more', hosts.length - EXAMPLE_HOSTS, {
        hosts: hosts.slice(0, EXAMPLE_HOSTS).join(', '),
        count: hosts.length - EXAMPLE_HOSTS
      })
    : hosts.join(', ')
}

function coverage(groups: number, finding: ValueFinding): TranslatedString {
  return _tn('in %{count} of %{total} group', 'in %{count} of %{total} groups', finding.groups, {
    count: groups,
    total: finding.groups
  })
}

function detectedCoverage(finding: ValueFinding, choice: ValueChoice): number {
  return (
    finding.told_apart?.values.find((counted) => counted.value === choice.markValue)?.groups ?? 0
  )
}

function addWord(): void {
  const word = newWord.value.trim().toLowerCase()
  if (!isNameWord(word)) {
    newWordErrors.value = [_t('Enter one whole part of a host name - without "-", "_" or ".".')]
    return
  }
  newWordErrors.value = []
  newWord.value = ''
  added.value = word
  emit('addWord', word)
}

function addValue(picked: string | null): void {
  const value = addableValues.value.get(picked ?? '')
  if (value) {
    added.value = value.name
    emit('addValue', value)
  }
}
</script>

<template>
  <div class="mode-host-relation-discovery-finding-list">
    <CmkParagraph v-if="nothingFound" class="mode-host-relation-discovery-finding-list__empty">
      {{
        inNames && inValues
          ? _t(
              'Checkmk found no hosts that obviously belong together - neither one named like another plus a word, "srv-01-ilo" next to "srv-01" for example, nor hosts sharing a value such as a serial number. If your hosts are named another way, enter the word or the label below.'
            )
          : inNames
            ? _t(
                'Checkmk found no host named like another plus a word - "srv-01-ilo" next to "srv-01", for example. If your hosts are named another way, enter the word below.'
              )
            : _t(
                'Checkmk found no label or attribute whose values each sit on a handful of hosts, the way a serial number does. Pick the one your hosts share below.'
              )
      }}
    </CmkParagraph>

    <section
      v-if="inNames && props.words.length > 0"
      class="mode-host-relation-discovery-finding-list__section"
    >
      <CmkHeading type="h4">{{ _t('In the host names') }}</CmkHeading>
      <CmkParagraph class="mode-host-relation-discovery-finding-list__example">
        {{
          _t(
            'Tick every word that marks a %{noun}. The host with the word in its name is the %{noun}, the other one its %{other}.',
            { noun, other: otherNoun }
          )
        }}
      </CmkParagraph>
      <ul v-if="knownWords.length > 0" class="mode-host-relation-discovery-finding-list__findings">
        <li
          v-for="finding in knownWords"
          :key="`word:${finding.word}`"
          class="mode-host-relation-discovery-finding-list__finding"
        >
          <CmkCheckbox
            class="mode-host-relation-discovery-finding-list__body"
            :model-value="isWordMeant(finding)"
            padding="top"
            @update:model-value="(meant) => setWordMeant(finding, meant)"
          >
            <template #label>
              <span class="mode-host-relation-discovery-finding-list__title">{{
                wordTitle(finding)
              }}</span>
            </template>
            <CmkParagraph class="mode-host-relation-discovery-finding-list__example">
              <template v-for="(example, index) in finding.examples" :key="example.named">
                <template v-if="index > 0">, </template>
                <span class="mode-host-relation-discovery-finding-list__host">{{
                  example.named
                }}</span>
                &middot;
                <span class="mode-host-relation-discovery-finding-list__host">{{
                  example.base
                }}</span>
              </template>
              <template v-if="finding.pairs > finding.examples.length">
                &ensp;{{ moreThanShown(finding.pairs - finding.examples.length) }}
              </template>
            </CmkParagraph>
          </CmkCheckbox>
        </li>
      </ul>
      <template v-if="otherWords.length > 0">
        <CmkParagraph
          v-if="knownWords.length > 0"
          class="mode-host-relation-discovery-finding-list__subheading"
        >
          {{ _t('Other words your host names use') }}
        </CmkParagraph>
        <ul class="mode-host-relation-discovery-finding-list__findings">
          <li
            v-for="finding in otherWords"
            :key="`word:${finding.word}`"
            class="mode-host-relation-discovery-finding-list__finding"
          >
            <CmkCheckbox
              class="mode-host-relation-discovery-finding-list__body"
              :model-value="isWordMeant(finding)"
              :disabled="finding.pairs === 0"
              padding="top"
              @update:model-value="(meant) => setWordMeant(finding, meant)"
            >
              <template #label>
                <span class="mode-host-relation-discovery-finding-list__title">{{
                  wordTitle(finding)
                }}</span>
              </template>
              <CmkParagraph
                v-if="finding.pairs > 0"
                class="mode-host-relation-discovery-finding-list__example"
              >
                <template v-for="(example, index) in finding.examples" :key="example.named">
                  <template v-if="index > 0">, </template>
                  <span class="mode-host-relation-discovery-finding-list__host">{{
                    example.named
                  }}</span>
                  &middot;
                  <span class="mode-host-relation-discovery-finding-list__host">{{
                    example.base
                  }}</span>
                </template>
                <template v-if="finding.pairs > finding.examples.length">
                  &ensp;{{ moreThanShown(finding.pairs - finding.examples.length) }}
                </template>
              </CmkParagraph>
            </CmkCheckbox>
            <CmkIconButton
              v-if="props.ownWords.includes(finding.word)"
              name="delete"
              size="small"
              :title="removeWordTitle(finding)"
              @click="emit('removeWord', finding.word)"
            />
          </li>
        </ul>
      </template>
    </section>

    <section
      v-if="inValues && props.values.length > 0"
      class="mode-host-relation-discovery-finding-list__section"
    >
      <CmkHeading type="h4">{{ _t('In host labels and custom host attributes') }}</CmkHeading>
      <CmkParagraph class="mode-host-relation-discovery-finding-list__example">
        {{
          _t(
            'Tick a label or attribute if the hosts sharing one of its values are a %{noun} and its %{other}.',
            { noun, other: otherNoun }
          )
        }}
      </CmkParagraph>
      <ul class="mode-host-relation-discovery-finding-list__findings">
        <li
          v-for="finding in props.values"
          :key="valueKey(finding)"
          class="mode-host-relation-discovery-finding-list__finding"
        >
          <CmkCheckbox
            class="mode-host-relation-discovery-finding-list__body"
            :model-value="isValueMeant(finding)"
            :disabled="finding.groups === 0"
            padding="top"
            @update:model-value="
              (meant) => updateValue(finding, { meaning: meant ? props.kind : NOT_RELATED })
            "
          >
            <template #label>
              <span class="mode-host-relation-discovery-finding-list__title">{{
                valueTitle(finding)
              }}</span>
            </template>
            <div class="mode-host-relation-discovery-finding-list__details">
              <CmkParagraph
                v-if="finding.examples.length > 0"
                class="mode-host-relation-discovery-finding-list__example"
              >
                <template v-for="example in finding.examples" :key="example.value">
                  <span class="mode-host-relation-discovery-finding-list__tag">
                    <CmkTag
                      :color="finding.source === 'label' ? 'label' : 'default'"
                      variant="fill"
                      size="small"
                      :content="valueTag(finding.name, example.value)"
                    />
                  </span>
                  <span class="mode-host-relation-discovery-finding-list__hosts">{{
                    exampleHosts(example.hosts)
                  }}</span>
                  &ensp;
                </template>
                <template v-if="finding.groups > finding.examples.length">
                  {{ moreThanShown(finding.groups - finding.examples.length) }}
                </template>
              </CmkParagraph>
              <CmkParagraph
                v-if="finding.too_wide > 0"
                class="mode-host-relation-discovery-finding-list__example"
              >
                {{ tooWide(finding) }}
              </CmkParagraph>
              <template v-if="isValueMeant(finding)">
                <!-- What Checkmk found says which host is which; changing it is the exception. -->
                <div
                  v-if="valueChoice(finding).marker === 'detected'"
                  class="mode-host-relation-discovery-finding-list__told-apart"
                >
                  <template v-if="finding.told_apart?.by === 'names'">
                    <CmkParagraph>
                      {{
                        _t('The %{noun} is the one with "%{words}" in its name, %{coverage}.', {
                          noun: noun,
                          words: finding.told_apart.words.join('", "'),
                          coverage: coverage(finding.told_apart.groups, finding)
                        })
                      }}
                    </CmkParagraph>
                  </template>
                  <template v-else-if="finding.told_apart?.by === 'value'">
                    <div class="mode-host-relation-discovery-finding-list__question">
                      <CmkLabel :for="`${idPrefix}-${valueKey(finding)}-detected`">{{
                        _t('The %{noun} is the one with %{name}:', {
                          noun: noun,
                          name: finding.told_apart.name ?? ''
                        })
                      }}</CmkLabel>
                      <CmkDropdown
                        :component-id="`${idPrefix}-${valueKey(finding)}-detected`"
                        :model-value="valueChoice(finding).markValue || null"
                        :options="detectedValues(finding)"
                        :input-hint="_t('Pick the value')"
                        :label="
                          _t('The %{noun} is the one with %{name}:', {
                            noun: noun,
                            name: finding.told_apart.name ?? ''
                          })
                        "
                        @update:model-value="
                          (value) => updateValue(finding, { markValue: value ?? '' })
                        "
                      />
                      <span
                        v-if="valueChoice(finding).markValue"
                        class="mode-host-relation-discovery-finding-list__example"
                        >{{
                          coverage(detectedCoverage(finding, valueChoice(finding)), finding)
                        }}</span
                      >
                    </div>
                  </template>
                  <CmkParagraph v-else>
                    {{
                      _t(
                        'Nothing in these hosts says which one is the %{noun}. You pick it for each group in the next step.',
                        { noun: noun }
                      )
                    }}
                  </CmkParagraph>
                  <CmkInlineButton icon="edit" @click="updateMarker(finding, 'ask')">
                    {{ _t('Tell them apart another way') }}
                  </CmkInlineButton>
                </div>

                <template v-else>
                  <CmkParagraph :id="`${idPrefix}-${valueKey(finding)}-which`">{{
                    _t('Which one is the %{noun}?', { noun: noun })
                  }}</CmkParagraph>
                  <CmkRadioGroup
                    :model-value="valueChoice(finding).marker"
                    :aria-labelledby="`${idPrefix}-${valueKey(finding)}-which`"
                    @update:model-value="(marker) => updateMarker(finding, marker)"
                  >
                    <CmkRadioButton
                      v-if="finding.told_apart"
                      value="detected"
                      :label="_t('The one Checkmk found')"
                    />
                    <CmkRadioButton
                      v-if="kindWords.length"
                      value="words"
                      :label="
                        _t('The one with one of these words in its name: %{words}', {
                          words: kindWords.join(', ')
                        })
                      "
                    />
                    <CmkRadioButton
                      v-if="props.labelNames.length > 0"
                      value="label"
                      :label="_t('The one with a certain host label')"
                    />
                    <CmkRadioButton
                      v-if="props.attributeNames.length > 0"
                      value="attribute"
                      :label="_t('The one with a certain custom host attribute')"
                    />
                    <CmkRadioButton
                      value="ask"
                      :label="_t('I will pick it in the next step, one group at a time')"
                    />
                  </CmkRadioGroup>
                  <div
                    v-if="isMarkedByValue(resolvedMarker(finding, valueChoice(finding)))"
                    class="mode-host-relation-discovery-finding-list__question"
                  >
                    <CmkLabel :for="`${idPrefix}-${valueKey(finding)}-name`">{{
                      valueChoice(finding).marker === 'label'
                        ? _t('Host label')
                        : _t('Custom host attribute')
                    }}</CmkLabel>
                    <CmkDropdown
                      :component-id="`${idPrefix}-${valueKey(finding)}-name`"
                      :model-value="valueChoice(finding).markName || null"
                      :options="
                        valueChoice(finding).marker === 'label' ? labelOptions : attributeOptions
                      "
                      :label="
                        valueChoice(finding).marker === 'label'
                          ? _t('Host label')
                          : _t('Custom host attribute')
                      "
                      :input-hint="_t('Choose one')"
                      @update:model-value="(name) => updateValue(finding, { markName: name ?? '' })"
                    />
                    <CmkLabel :for="`${idPrefix}-${valueKey(finding)}-value`">{{
                      _t('with the value')
                    }}</CmkLabel>
                    <CmkInput
                      :id="`${idPrefix}-${valueKey(finding)}-value`"
                      :model-value="valueChoice(finding).markValue"
                      field-size="medium"
                      placeholder="board"
                      @update:model-value="
                        (value) => updateValue(finding, { markValue: String(value ?? '') })
                      "
                    />
                  </div>
                </template>
                <CmkParagraph
                  v-if="!isComplete(finding, valueChoice(finding))"
                  class="mode-host-relation-discovery-finding-list__example"
                >
                  {{
                    _t('Say which value the %{noun} carries to continue.', {
                      noun: noun
                    })
                  }}
                </CmkParagraph>
              </template>
            </div>
          </CmkCheckbox>
          <CmkIconButton
            v-if="props.ownValues.includes(valueKey(finding))"
            name="delete"
            size="small"
            :title="removeValueTitle(finding)"
            @click="emit('removeValue', { source: finding.source, name: finding.name })"
          />
        </li>
      </ul>
    </section>

    <section class="mode-host-relation-discovery-finding-list__section">
      <CmkCollapsibleTitle
        :title="_t('Additional indicators')"
        :open="addingOpen || nothingFound"
        @toggle-open="addingOpen = !addingOpen"
      />
      <CmkCollapsible :open="addingOpen || nothingFound">
        <div class="mode-host-relation-discovery-finding-list__adding">
          <div v-if="inNames" class="mode-host-relation-discovery-finding-list__question">
            <CmkLabel :for="newWordId">{{ _t('A word in host names') }}</CmkLabel>
            <CmkInput
              :id="newWordId"
              v-model="newWord"
              field-size="medium"
              :external-errors="newWordErrors"
              placeholder="oob"
              @keydown.enter.prevent="addWord"
            />
            <CmkButton :disabled="props.busy || newWord.trim() === ''" @click="addWord">
              {{ _t('Add word') }}
            </CmkButton>
          </div>
          <div
            v-if="inValues && (props.labelNames.length > 0 || props.attributeNames.length > 0)"
            class="mode-host-relation-discovery-finding-list__question"
          >
            <CmkLabel :for="addValueId">{{ _t('A value hosts share') }}</CmkLabel>
            <CmkDropdown
              :component-id="addValueId"
              :model-value="null"
              :options="sharedValueOptions"
              :label="_t('A value hosts share')"
              :input-hint="_t('Pick a label or attribute')"
              :disabled="props.busy"
              @update:model-value="addValue"
            />
          </div>
          <!-- The finding appears in the list above, out of sight of the field it was typed
               into: this is where the user looks, so this is where it is said. -->
          <CmkParagraph
            v-if="props.busy && added"
            class="mode-host-relation-discovery-finding-list__example"
            role="status"
          >
            {{ _t('Looking for "%{name}" in all hosts...', { name: added }) }}
          </CmkParagraph>
          <CmkParagraph
            v-else-if="added"
            class="mode-host-relation-discovery-finding-list__example"
            role="status"
          >
            {{ _t('"%{name}" has been looked up and is listed above.', { name: added }) }}
          </CmkParagraph>
        </div>
      </CmkCollapsible>
    </section>
  </div>
</template>

<style scoped>
.mode-host-relation-discovery-finding-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-double);
}

.mode-host-relation-discovery-finding-list__section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-half);
}

/* One box per section, its findings set apart by a rule rather than a box each. */
.mode-host-relation-discovery-finding-list__findings {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0 var(--spacing);
  list-style: none;
  border: 1px solid var(--ux-theme-4);
  border-radius: var(--border-radius);
}

.mode-host-relation-discovery-finding-list__finding {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing);
  padding: var(--spacing) 0;
  border-bottom: 1px solid var(--ux-theme-4);
}

.mode-host-relation-discovery-finding-list__finding:last-child {
  border-bottom: none;
}

.mode-host-relation-discovery-finding-list__body {
  flex: 1;
}

.mode-host-relation-discovery-finding-list__details {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--spacing-half);
}

.mode-host-relation-discovery-finding-list__subheading {
  padding-top: var(--spacing-half);
  font-weight: var(--font-weight-bold);
}

.mode-host-relation-discovery-finding-list__title {
  font-weight: var(--font-weight-bold);
}

.mode-host-relation-discovery-finding-list__example,
.mode-host-relation-discovery-finding-list__empty {
  color: var(--font-color-dimmed);
}

.mode-host-relation-discovery-finding-list__host,
.mode-host-relation-discovery-finding-list__hosts {
  color: var(--font-color);
}

/* A host name and a label tag read as one thing each; broken over two lines they do not. */
.mode-host-relation-discovery-finding-list__host,
.mode-host-relation-discovery-finding-list__tag {
  white-space: nowrap;
}

.mode-host-relation-discovery-finding-list__question,
.mode-host-relation-discovery-finding-list__told-apart {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacing-half);
}

.mode-host-relation-discovery-finding-list__adding {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  padding-top: var(--spacing-half);
}
</style>
