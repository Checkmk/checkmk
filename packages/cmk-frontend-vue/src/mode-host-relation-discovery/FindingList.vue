<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkCollapsible, { CmkCollapsibleTitle } from 'cmk-ui-library/components/CmkCollapsible'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import useId from 'cmk-ui-library/lib/useId'
import { computed, ref } from 'vue'

import type { WordChoice, WordFinding } from './types'
import { NOT_RELATED, isNameWord } from './types'

const { _t, _tn } = usei18n()

const props = defineProps<{
  words: WordFinding[]
  /** Per kind of relation, the end a finding marks, by the name the wire uses for it. */
  kinds: Record<string, string>
  /** The kind the user looks for: what every finding ticked here stands for. */
  kind: string
  relationNouns: Record<string, string>
  ownWords: string[]
  busy: boolean
}>()

const emit = defineEmits<{
  addWord: [word: string]
  removeWord: [word: string]
}>()

const wordChoices = defineModel<Record<string, WordChoice>>('wordChoices', { required: true })

const newWordId = useId()

const newWord = ref('')

const newWordErrors = ref<string[]>([])

const addingOpen = ref(false)

/** What the user added last, to say next to the field where it went. */
const added = ref('')

const nothingFound = computed(() => props.words.length === 0)

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

function removeWordTitle(finding: WordFinding): TranslatedString {
  return _t('Remove the word "%{word}"', { word: finding.word })
}

function moreThanShown(count: number): TranslatedString {
  return _tn('and 1 more', 'and %{count} more', count, { count })
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

function isWordMeant(finding: WordFinding): boolean {
  return finding.pairs > 0 && wordChoice(finding).meaning === props.kind
}

function setWordMeant(finding: WordFinding, meant: boolean): void {
  wordChoices.value = {
    ...wordChoices.value,
    [finding.word]: { meaning: meant ? props.kind : NOT_RELATED }
  }
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
</script>

<template>
  <div class="mode-host-relation-discovery-finding-list">
    <CmkParagraph v-if="nothingFound" class="mode-host-relation-discovery-finding-list__empty">
      {{
        _t(
          'Checkmk found no host named like another plus a word - "srv-01-ilo" next to "srv-01", for example. If your hosts are named another way, enter the word below.'
        )
      }}
    </CmkParagraph>

    <section
      v-if="props.words.length > 0"
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

    <section class="mode-host-relation-discovery-finding-list__section">
      <CmkCollapsibleTitle
        :title="_t('Something missing?')"
        :open="addingOpen || nothingFound"
        @toggle-open="addingOpen = !addingOpen"
      />
      <CmkCollapsible :open="addingOpen || nothingFound">
        <div class="mode-host-relation-discovery-finding-list__adding">
          <div class="mode-host-relation-discovery-finding-list__question">
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

/* A host name reads as one thing; broken over two lines it does not. */
.mode-host-relation-discovery-finding-list__host {
  color: var(--font-color);
  white-space: nowrap;
}

.mode-host-relation-discovery-finding-list__question {
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
