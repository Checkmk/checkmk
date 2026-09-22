<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

import ImagePicker from '@/maps/image-library/components/ImagePicker.vue'
import { useMapsApis } from '@/maps/services/context'
import type { PresentationElement, PresentationTheme, PresentationView } from '@/maps/types/api'

import { isBindable } from '../binding'
import { ICONS, SLIDE_PRESETS } from '../chrome'
import { themeOptions, themeTokens } from '../themes'
import ColorField from './ColorField.vue'
import PresentationGlyph from './PresentationGlyph.vue'
import InspectorAppearanceSection from './inspector/InspectorAppearanceSection.vue'
import InspectorDataSection from './inspector/InspectorDataSection.vue'
import InspectorImageSection from './inspector/InspectorImageSection.vue'
import InspectorLayoutSection from './inspector/InspectorLayoutSection.vue'
import InspectorTypographySection from './inspector/InspectorTypographySection.vue'

const { images } = useMapsApis()

const { _t } = usei18n()

const props = defineProps<{
  selection: PresentationElement[]
  view: PresentationView
  connectionId: string
  targets: { id: string; name: string }[]
  backgroundImageName: string
  saveLabel: string
}>()

const emit = defineEmits<{
  patch: [Record<string, unknown>]
  delete: []
  duplicate: []
  slide: [Partial<PresentationView>]
  save: []
  group: []
  ungroup: []
  /** Reopen the template gallery, which greets an empty slide on its own. */
  'browse-templates': []
}>()

// On change rather than on input: the slide size is clamped to its minimum,
// and clamping a half-typed "2" back into the field makes the width untypeable.
function onSideChange(key: 'width' | 'height', e: Event): void {
  const v = (e.target as HTMLInputElement).valueAsNumber
  if (Number.isFinite(v)) {
    emit('slide', { [key]: v })
  }
}

const hasGroup = computed(() => props.selection.some((e) => e.kind === 'group'))

const single = computed(() => (props.selection.length === 1 ? props.selection[0] : undefined))

// The panel is contextual (Figma-style): selecting follows to the Element tab,
// deselecting falls back to Slide. The tabs make the current context explicit
// and let the operator inspect slide settings without dropping the selection.
const tab = ref<'slide' | 'element'>('slide')
watch(
  () => props.selection.length,
  (n) => {
    tab.value = n > 0 ? 'element' : 'slide'
  },
  { immediate: true }
)

// A connector's x/y/w/h is vestigial (its endpoints drive the geometry), and a
// group's box doesn't move its children — neither gets the Layout numbers.
const showLayout = computed(() => {
  const el = single.value
  if (!el || el.kind === 'group') {
    return false
  }
  return !(el.kind === 'shape' && (el.shape === 'line' || el.shape === 'arrow'))
})

function kindTitle(el: PresentationElement): string {
  if (el.kind === 'text') {
    return _t('Text')
  }
  if (el.kind === 'image') {
    return _t('Image')
  }
  if (el.kind === 'data') {
    return _t('Live status')
  }
  if (el.kind === 'group') {
    return _t('Group')
  }
  return el.shape.charAt(0).toUpperCase() + el.shape.slice(1)
}

function onRename(e: Event): void {
  const name = (e.target as HTMLInputElement).value.trim()
  emit('patch', { name: name || null })
}

const multiOpacity = computed(() => {
  if (!props.selection.length) {
    return 1
  }
  return Math.max(...props.selection.map((e) => e.opacity))
})
function onMultiOpacity(e: Event): void {
  emit('patch', { opacity: Number((e.target as HTMLInputElement).value) / 100 })
}

// Direct background upload into the image library — the picker stays for
// re-using existing images; emitting the slide patch rides the auto-save.
const bgFileInput = ref<HTMLInputElement | null>(null)
const bgUploading = ref(false)
const bgUploadError = ref('')

async function onBgUpload(e: Event): Promise<void> {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) {
    return
  }
  bgUploading.value = true
  bgUploadError.value = ''
  try {
    const entry = await images.upload(file)
    emit('slide', { background_image: entry.name })
  } catch (err) {
    bgUploadError.value = err instanceof Error ? err.message : _t('Upload failed')
  } finally {
    bgUploading.value = false
  }
}

const themeDropdownOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: themeOptions().map((t) => ({ name: t.name, title: untranslated(t.title) }))
}))

const slidePresets = SLIDE_PRESETS
</script>

<template>
  <aside class="maps-presentation-inspector-panel" @pointerdown.stop @dblclick.stop>
    <div class="maps-presentation-inspector-panel__topbar">
      <div class="maps-presentation-inspector-panel__tabs">
        <button
          class="maps-presentation-inspector-panel__tab"
          :class="{ 'maps-presentation-inspector-panel__tab--on': tab === 'slide' }"
          @click="tab = 'slide'"
        >
          {{ _t('Slide') }}
        </button>
        <button
          class="maps-presentation-inspector-panel__tab"
          :class="{ 'maps-presentation-inspector-panel__tab--on': tab === 'element' }"
          :disabled="!selection.length"
          :title="selection.length ? undefined : _t('Select an element on the slide')"
          @click="tab = 'element'"
        >
          {{ _t('Element') }}
        </button>
      </div>
      <div class="maps-presentation-inspector-panel__save">
        <span class="maps-presentation-inspector-panel__save-label">{{ saveLabel }}</span>
        <button
          class="maps-presentation-inspector-panel__icon"
          :title="_t('Save now')"
          @click="emit('save')"
        >
          <PresentationGlyph :svg="ICONS.save" />
        </button>
      </div>
    </div>

    <template v-if="tab === 'element' && single">
      <div class="maps-presentation-inspector-panel__head">
        <input
          class="maps-presentation-inspector-panel__name"
          :value="single.name ?? ''"
          :placeholder="kindTitle(single)"
          :title="_t('Element name')"
          @change="onRename"
        />
        <div class="maps-presentation-inspector-panel__actions">
          <button
            class="maps-presentation-inspector-panel__icon"
            :title="_t('Duplicate')"
            @click="emit('duplicate')"
          >
            <PresentationGlyph :svg="ICONS.duplicate" />
          </button>
          <button
            class="maps-presentation-inspector-panel__icon maps-presentation-inspector-panel__icon--danger"
            :title="_t('Delete')"
            @click="emit('delete')"
          >
            <PresentationGlyph :svg="ICONS.trash" />
          </button>
        </div>
      </div>
      <CmkScrollContainer class="maps-presentation-inspector-panel__body-wrap">
        <div class="maps-presentation-inspector-panel__body">
          <template v-if="single.kind === 'group'">
            <div class="maps-presentation-inspector-panel__hint">
              {{ _t('Group — move or duplicate it as one unit.') }}
            </div>
            <CmkButton class="maps-presentation-inspector-panel__grow" @click="emit('ungroup')">
              {{ _t('Ungroup') }}
            </CmkButton>
          </template>
          <InspectorLayoutSection
            v-if="showLayout"
            :element="single"
            @patch="emit('patch', $event)"
          />
          <InspectorTypographySection
            v-if="single.kind === 'text'"
            :element="single"
            :theme="view.theme"
            @patch="emit('patch', $event)"
          />
          <InspectorAppearanceSection
            v-if="single.kind === 'shape'"
            :element="single"
            :theme="view.theme"
            @patch="emit('patch', $event)"
          />
          <InspectorImageSection
            v-if="single.kind === 'image'"
            :element="single"
            @patch="emit('patch', $event)"
          />
          <InspectorDataSection
            v-if="isBindable(single)"
            :element="single"
            :connection-id="connectionId"
            :targets="targets"
            :theme="view.theme"
            @patch="emit('patch', $event)"
          />
        </div>
      </CmkScrollContainer>
    </template>

    <template v-else-if="tab === 'element' && selection.length > 1">
      <div class="maps-presentation-inspector-panel__head">
        <span class="maps-presentation-inspector-panel__title">{{
          _t('%{n} elements selected', { n: String(selection.length) })
        }}</span>
        <div class="maps-presentation-inspector-panel__actions">
          <button
            class="maps-presentation-inspector-panel__icon"
            :title="_t('Duplicate')"
            @click="emit('duplicate')"
          >
            <PresentationGlyph :svg="ICONS.duplicate" />
          </button>
          <button
            class="maps-presentation-inspector-panel__icon maps-presentation-inspector-panel__icon--danger"
            :title="_t('Delete')"
            @click="emit('delete')"
          >
            <PresentationGlyph :svg="ICONS.trash" />
          </button>
        </div>
      </div>
      <div class="maps-presentation-inspector-panel__body">
        <div class="maps-presentation-inspector-panel__row">
          <span class="maps-cap">{{ _t('Opacity') }}</span>
          <input
            class="maps-range"
            type="range"
            min="0"
            max="100"
            :value="Math.round(multiOpacity * 100)"
            @input="onMultiOpacity"
          />
          <span class="maps-range-pct">{{ Math.round(multiOpacity * 100) }}%</span>
        </div>
        <div class="maps-presentation-inspector-panel__row">
          <CmkButton class="maps-presentation-inspector-panel__grow" @click="emit('group')">{{
            _t('Group')
          }}</CmkButton>
          <CmkButton
            class="maps-presentation-inspector-panel__grow"
            :disabled="!hasGroup"
            @click="emit('ungroup')"
          >
            {{ _t('Ungroup') }}
          </CmkButton>
        </div>
        <div class="maps-presentation-inspector-panel__hint">
          {{ _t('Use the toolbar above the slide to align and distribute.') }}
        </div>
      </div>
    </template>

    <template v-else>
      <CmkScrollContainer class="maps-presentation-inspector-panel__body-wrap">
        <div class="maps-presentation-inspector-panel__body">
          <section class="maps-presentation-inspector-panel__section">
            <h3 class="maps-section-title">{{ _t('Theme') }}</h3>
            <CmkDropdown
              :model-value="view.theme"
              :options="themeDropdownOptions"
              :width="'fill'"
              :label="_t('Theme')"
              @update:model-value="emit('slide', { theme: $event as PresentationTheme })"
            />
          </section>
          <section class="maps-presentation-inspector-panel__section">
            <h3 class="maps-section-title">{{ _t('Aspect / size') }}</h3>
            <div class="maps-presentation-inspector-panel__presets">
              <button
                v-for="p in slidePresets"
                :key="p.label"
                class="maps-presentation-inspector-panel__preset"
                :class="{
                  'maps-presentation-inspector-panel__preset--on':
                    view.width === p.w && view.height === p.h
                }"
                @click="emit('slide', { width: p.w, height: p.h })"
              >
                {{ p.label }}
              </button>
            </div>
            <div class="maps-presentation-inspector-panel__row">
              <label class="maps-presentation-inspector-panel__num">
                <span class="maps-cap">{{ _t('Width') }}</span>
                <CmkInput
                  type="number"
                  :model-value="view.width"
                  min="320"
                  max="8192"
                  @change="onSideChange('width', $event)"
                />
              </label>
              <label class="maps-presentation-inspector-panel__num">
                <span class="maps-cap">{{ _t('Height') }}</span>
                <CmkInput
                  type="number"
                  :model-value="view.height"
                  min="320"
                  max="8192"
                  @change="onSideChange('height', $event)"
                />
              </label>
            </div>
          </section>
          <section class="maps-presentation-inspector-panel__section">
            <h3 class="maps-section-title">{{ _t('Background') }}</h3>
            <div class="maps-presentation-inspector-panel__row">
              <ColorField
                :label="_t('Background color')"
                :value="view.background ?? null"
                :default-color="themeTokens(view.theme)['--pres-bg']"
                @set="emit('slide', { background: $event })"
              />
              <span
                class="maps-presentation-inspector-panel__hint maps-presentation-inspector-panel__hint--inline"
                >{{ view.background ? view.background : _t('Theme default') }}</span
              >
            </div>
            <ImagePicker
              :model-value="backgroundImageName"
              :placeholder="_t('Background image…')"
              kind="image"
              @update:model-value="emit('slide', { background_image: $event || null })"
            />
            <CmkButton
              class="maps-presentation-inspector-panel__grow"
              :disabled="bgUploading"
              @click="bgFileInput?.click()"
            >
              {{ bgUploading ? _t('Uploading…') : _t('Upload background image…') }}
            </CmkButton>
            <input
              ref="bgFileInput"
              type="file"
              accept="image/png,image/jpeg,image/svg+xml,image/webp,image/gif"
              class="maps-presentation-inspector-panel__hidden-file"
              @change="onBgUpload"
            />
            <p v-if="bgUploadError" class="maps-presentation-inspector-panel__error">
              {{ bgUploadError }}
            </p>
          </section>
          <section class="maps-presentation-inspector-panel__section">
            <CmkButton @click="emit('browse-templates')">
              {{ _t('Browse templates…') }}
            </CmkButton>
          </section>
        </div>
      </CmkScrollContainer>
    </template>
  </aside>
</template>

<style scoped>
.maps-presentation-inspector-panel {
  display: flex;
  flex-direction: column;
  width: 280px;
  flex-shrink: 0;
  background: var(--ux-theme-3);
  border-left: 1px solid var(--default-border-color, rgb(255 255 255 / 8%));
  color: var(--font-color);
  z-index: 5;
}

.maps-presentation-inspector-panel__topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-4);
  padding: 8px 12px;
  border-bottom: 1px solid var(--default-border-color, rgb(255 255 255 / 8%));
}

.maps-presentation-inspector-panel__tabs {
  display: flex;
  gap: var(--dimension-2);
  padding: var(--dimension-2);
  border-radius: 7px;
  background: var(--ux-theme-1, rgb(0 0 0 / 20%));
}

.maps-presentation-inspector-panel__tab {
  padding: 4px 12px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: var(--font-color-dimmed);
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-bold);
  cursor: pointer;
}

.maps-presentation-inspector-panel__tab--on {
  background: var(--ux-theme-3);
  color: var(--font-color);
  box-shadow: 0 1px 3px rgb(0 0 0 / 30%);
}

.maps-presentation-inspector-panel__tab:disabled {
  opacity: 0.4;
  cursor: default;
}

.maps-presentation-inspector-panel__save {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  min-width: 0;
}

.maps-presentation-inspector-panel__save-label {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
  white-space: nowrap;
}

.maps-presentation-inspector-panel__grow {
  flex: 1;
  justify-content: center;
}

.maps-presentation-inspector-panel__hidden-file {
  display: none;
}

.maps-presentation-inspector-panel__error {
  margin: 0;
  font-size: var(--font-size-normal);
  color: var(--color-state-critical);
}

.maps-presentation-inspector-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-4);
  padding: 8px 12px;
  border-bottom: 1px solid var(--default-border-color, rgb(255 255 255 / 8%));
  min-height: 44px;
  box-sizing: border-box;
}

.maps-presentation-inspector-panel__title {
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-large);
}

.maps-presentation-inspector-panel__name {
  flex: 1;
  min-width: 0;
  padding: 4px 6px;
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-large);
  color: var(--font-color);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
}

.maps-presentation-inspector-panel__name:hover {
  border-color: var(--default-form-element-border-color);
}

.maps-presentation-inspector-panel__name:focus {
  outline: none;
  border-color: var(--color-corporate-green-50);
  background: var(--default-form-element-bg-color);
}

.maps-presentation-inspector-panel__actions {
  display: flex;
  gap: var(--dimension-2);
}

.maps-presentation-inspector-panel__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: var(--font-color-dimmed);
  cursor: pointer;
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
.maps-presentation-inspector-panel__icon :deep(svg) {
  width: 16px;
  height: 16px;
}

.maps-presentation-inspector-panel__icon:hover {
  background: var(--input-hover-bg-color, rgb(255 255 255 / 8%));
  color: var(--font-color);
}

.maps-presentation-inspector-panel__icon--danger:hover {
  background: color-mix(in srgb, var(--color-danger) 20%, transparent);
}

.maps-presentation-inspector-panel__body-wrap {
  flex: 1;
  min-height: 0;
}

.maps-presentation-inspector-panel__body {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
  padding: var(--dimension-5);
}

.maps-presentation-inspector-panel__section {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.maps-presentation-inspector-panel__row {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.maps-presentation-inspector-panel__num {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  flex: 1;
  min-width: 0;
}

.maps-presentation-inspector-panel__presets {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}

.maps-presentation-inspector-panel__preset {
  padding: 6px 4px;
  border: 1px solid var(--default-form-element-border-color);
  border-radius: 6px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: var(--font-size-normal);
}

.maps-presentation-inspector-panel__preset:hover {
  background: var(--input-hover-bg-color, rgb(255 255 255 / 6%));
}

.maps-presentation-inspector-panel__preset--on {
  border-color: var(--color-corporate-green-50);
  background: color-mix(in srgb, var(--color-corporate-green-50) 18%, transparent);
}

.maps-presentation-inspector-panel__hint {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
  line-height: 1.4;
}

.maps-presentation-inspector-panel__hint--inline {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
