<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import { type PanelState } from '@ucl/_ucl/types/prop-panel'
import { type IconSizeNames } from 'cmk-ui-library/components/CmkIcon'

// Titles for every CmkIcon size. Keyed by IconSizeNames so adding or removing a
// size in the registry forces this list to be updated (it cannot silently drift).
const sizeTitles: Record<IconSizeNames, string> = {
  xxsmall: 'XX-small',
  xsmall: 'X-small',
  small: 'Small',
  medium: 'Medium',
  large: 'Large',
  xlarge: 'X-large',
  xxlarge: 'XX-large',
  xxxlarge: 'XXX-large'
}

export const panelConfig = {
  filter: {
    type: 'string' as const,
    title: 'Search',
    initialState: '',
    help: 'Substring match against the icon name (e.g. check, alert, host).'
  },
  cmkIcon: {
    type: 'boolean' as const,
    title: 'CmkIcon',
    initialState: true,
    help: 'Show the themed/unthemed bitmap and SVG icons rendered by <CmkIcon>.'
  },
  cmkMultitoneIcon: {
    type: 'boolean' as const,
    title: 'CmkMultitoneIcon',
    initialState: true,
    help: 'Show the colorizable inline-SVG icons rendered by <CmkMultitoneIcon>.'
  },
  type: {
    type: 'list' as const,
    title: 'Image type',
    options: [
      { title: 'All', name: 'all' },
      { title: 'SVG', name: 'svg' },
      { title: 'PNG', name: 'png' }
    ],
    initialState: 'all',
    help: 'Restrict the grid to a single underlying image format.'
  },
  size: {
    type: 'list' as const,
    title: 'Preview size',
    options: Object.entries(sizeTitles).map(([name, title]) => ({
      title,
      name: name as IconSizeNames
    })),
    initialState: 'xxlarge',
    help: 'Rendered size of the icon previews.'
  },
  emblem: {
    type: 'boolean' as const,
    title: 'Add emblem',
    initialState: false,
    help: 'Compose every preview with an emblem, picked from the box below these filters.'
  }
} satisfies PanelConfig & PanelConfigFor<unknown>
</script>

<script setup lang="ts">
import {
  type ExternalReferenceItem,
  UclDetailPageComponent,
  UclDetailPageExternalReference,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import CmkCopy from 'cmk-ui-library/components/CmkCopy.vue'
import { type SimpleIcons } from 'cmk-ui-library/components/CmkIcon'
import CmkIconEmblem from 'cmk-ui-library/components/CmkIcon/CmkIconEmblem.vue'
import {
  emblems,
  iconSizes,
  oneColorIcons,
  themedIcons,
  twoColorIcons,
  unthemedIcons
} from 'cmk-ui-library/components/CmkIcon/icons.constants'
import type { IconEmblems } from 'cmk-ui-library/components/CmkIcon/types'
import { getIconPath } from 'cmk-ui-library/components/CmkIcon/utils'
import { useTheme } from 'cmk-ui-library/lib/useTheme'
import { PopoverContent, PopoverPortal, PopoverRoot, PopoverTrigger } from 'reka-ui'
import { computed, ref } from 'vue'

import UclIconPreview, {
  type IconEntry,
  type IconType,
  MULTITONE_PRIMARY,
  MULTITONE_SECONDARY
} from './UclIconPreview.vue'
import { iconSearchLabels } from './iconSearchLabels'

defineProps<{ screenshotMode: boolean }>()

const { theme } = useTheme()

// The resolved asset URL can carry a query suffix (e.g. ?url&no-inline) and a
// content hash, so match the extension rather than the whole string.
function imageType(path: string): IconType {
  return /\.png(\?|$)/i.test(path) ? 'png' : 'svg'
}
// Completes an entry's derived fields (key, search) from its core properties.
function buildEntry(core: Omit<IconEntry, 'key' | 'search'>): IconEntry {
  return {
    ...core,
    key: `${core.kind}:${core.name}`,
    search: [core.name, ...(iconSearchLabels[core.name] ?? [])].join(' ').toLowerCase()
  }
}

// <CmkIcon> icons: the union of the unthemed map (one asset shared by both
// themes) and the per-theme map (separate light/dark assets), read live so the
// grid never drifts from the registry.
const cmkIcons = computed<IconEntry[]>(() => {
  const themedNames = new Set<string>([
    ...Object.keys(themedIcons.light),
    ...Object.keys(themedIcons.dark)
  ])
  const names = new Set<string>([...Object.keys(unthemedIcons), ...themedNames])
  return [...names]
    .map((name) => ({ name, path: getIconPath(name as SimpleIcons, theme.value) }))
    .filter(({ path }) => path !== '')
    .map(({ name, path }) =>
      buildEntry({
        name,
        kind: 'CmkIcon',
        type: imageType(path),
        themed: themedNames.has(name),
        twoColor: false
      })
    )
})

// <CmkMultitoneIcon> icons: always inline SVG, colorized at runtime.
const multitoneIcons = computed<IconEntry[]>(() =>
  [
    ...oneColorIcons.map((name) => ({ name, twoColor: false })),
    ...twoColorIcons.map((name) => ({ name, twoColor: true }))
  ].map(({ name, twoColor }) =>
    buildEntry({
      name,
      kind: 'CmkMultitoneIcon',
      type: 'svg',
      themed: false,
      twoColor
    })
  )
)

const propState = ref<PanelState>({
  filter: panelConfig.filter.initialState,
  cmkIcon: panelConfig.cmkIcon.initialState,
  cmkMultitoneIcon: panelConfig.cmkMultitoneIcon.initialState,
  type: panelConfig.type.initialState,
  size: panelConfig.size.initialState,
  emblem: panelConfig.emblem.initialState
})

const pickedEmblem = ref<IconEmblems>('rulesets')

const activeEmblem = computed<IconEmblems | undefined>(() =>
  propState.value['emblem'] ? pickedEmblem.value : undefined
)

const previewSize = computed(() => propState.value['size'] as IconSizeNames)

const previewSizePx = computed(() => `${iconSizes[previewSize.value]}px`)

const allIcons = computed<IconEntry[]>(() => {
  const entries: IconEntry[] = []
  if (propState.value['cmkIcon']) {
    entries.push(...cmkIcons.value)
  }
  if (propState.value['cmkMultitoneIcon']) {
    entries.push(...multitoneIcons.value)
  }
  return entries.sort((a, b) => a.name.localeCompare(b.name) || a.kind.localeCompare(b.kind))
})

const filtered = computed(() => {
  const needle = (propState.value['filter'] as string).trim().toLowerCase()
  const type = propState.value['type'] as string
  return allIcons.value.filter((icon) => {
    if (needle && !icon.search.includes(needle)) {
      return false
    }
    if (type !== 'all' && icon.type !== type) {
      return false
    }
    return true
  })
})

function iconSnippet(icon: IconEntry): string {
  if (icon.kind === 'CmkMultitoneIcon') {
    return icon.twoColor
      ? `<CmkMultitoneIcon name="${icon.name}" primary-color="${MULTITONE_PRIMARY}" secondary-color="${MULTITONE_SECONDARY}" />`
      : `<CmkMultitoneIcon name="${icon.name}" primary-color="${MULTITONE_PRIMARY}" />`
  }
  return `<CmkIcon name="${icon.name}" />`
}

function htmlSnippet(icon: IconEntry): string {
  const inner = iconSnippet(icon)
  if (activeEmblem.value === undefined) {
    return inner
  }
  return `<CmkIconEmblem emblem="${activeEmblem.value}">${inner}</CmkIconEmblem>`
}

const externalReferences: ExternalReferenceItem[] = [
  {
    label: 'Icons8',
    href: 'https://icons8.com',
    description:
      'Icons8 is the single source of truth for all icons used in the product. If a new icon is needed, it should be selected from the Icons8 library and aligned with the UX team.'
  },
  {
    label: 'Icons8 Claude skill',
    command: '/icons8-multitone-icon',
    description: 'Devs can use the skill to migrate from Icons8'
  },
  {
    label: 'iconSearchLabels.ts',
    file: 'packages/cmk-frontend-vue/ui-component-library/foundations/Icons/iconSearchLabels.ts',
    description: 'Search keywords/synonyms for the icon grid — add entries here'
  }
]
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>Icons</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-icons">
        <p class="ucl-icons__hint">
          All icons available to <code>&lt;CmkIcon&gt;</code> and
          <code>&lt;CmkMultitoneIcon&gt;</code>, read live from the icon registry so this view
          always reflects the currently loaded theme. Each card shows the icon and its underlying
          image type (<code>SVG</code> or <code>PNG</code>). Click a card to copy its name or
          ready-to-paste markup. Turn on <em>Add emblem</em> to compose every icon with one of the
          <code>&lt;CmkIconEmblem&gt;</code> badges offered beneath the filters; the copied markup
          then carries the wrapper too.
        </p>

        <div class="ucl-icons__count">{{ filtered.length }} of {{ allIcons.length }} icons</div>

        <div class="ucl-icons__grid" :style="{ '--ucl-icons-preview-size': previewSizePx }">
          <PopoverRoot v-for="icon in filtered" :key="icon.key">
            <PopoverTrigger as-child>
              <button type="button" class="ucl-icons__card" :title="icon.name">
                <span
                  class="ucl-icons__preview"
                  :class="{ 'ucl-icons__preview--emblem': activeEmblem !== undefined }"
                >
                  <CmkIconEmblem v-if="activeEmblem" :emblem="activeEmblem"
                    ><UclIconPreview :icon="icon" :size="previewSize"
                  /></CmkIconEmblem>
                  <UclIconPreview v-else :icon="icon" :size="previewSize" />
                </span>
                <span class="ucl-icons__name">{{ icon.name }}</span>
                <span class="ucl-icons__meta">
                  <span class="ucl-icons__badge" :class="`ucl-icons__badge--${icon.type}`">
                    {{ icon.type }}
                  </span>
                  <span
                    v-if="icon.kind === 'CmkMultitoneIcon'"
                    class="ucl-icons__badge ucl-icons__badge--multitone"
                  >
                    multitone
                  </span>
                  <span v-if="icon.themed" class="ucl-icons__badge ucl-icons__badge--themed">
                    themed
                  </span>
                </span>
              </button>
            </PopoverTrigger>
            <PopoverPortal>
              <PopoverContent side="top" align="center" :side-offset="6" as-child>
                <div class="ucl-icons__popover">
                  <div class="ucl-icons__popover-head">
                    <CmkIconEmblem v-if="activeEmblem" :emblem="activeEmblem"
                      ><UclIconPreview :icon="icon" size="large"
                    /></CmkIconEmblem>
                    <UclIconPreview v-else :icon="icon" size="large" />
                    <span class="ucl-icons__popover-name">{{ icon.name }}</span>
                  </div>
                  <CmkCopy :text="icon.name">
                    <button type="button" class="ucl-icons__copy-option">
                      <span class="ucl-icons__copy-label">name</span>
                      <span class="ucl-icons__copy-value">{{ icon.name }}</span>
                    </button>
                  </CmkCopy>
                  <CmkCopy :text="htmlSnippet(icon)">
                    <button type="button" class="ucl-icons__copy-option">
                      <span class="ucl-icons__copy-label">html</span>
                      <span class="ucl-icons__copy-value">{{ htmlSnippet(icon) }}</span>
                    </button>
                  </CmkCopy>
                </div>
              </PopoverContent>
            </PopoverPortal>
          </PopoverRoot>
        </div>

        <p v-if="filtered.length === 0" class="ucl-icons__empty">
          No icons match the current filters.
        </p>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" title="Filters" />

        <div v-if="propState['emblem']" class="ucl-icons__emblems">
          <div class="ucl-icons__emblems-title">Emblem</div>
          <div class="ucl-icons__emblems-grid">
            <button
              v-for="emblem in emblems"
              :key="emblem"
              type="button"
              class="ucl-icons__emblem-card"
              :class="{ 'ucl-icons__emblem-card--picked': emblem === pickedEmblem }"
              :aria-pressed="emblem === pickedEmblem"
              @click="pickedEmblem = emblem"
            >
              <CmkIconEmblem :emblem="emblem">
                <span class="ucl-icons__emblem-base" />
              </CmkIconEmblem>
              <span class="ucl-icons__name">{{ emblem }}</span>
            </button>
          </div>
        </div>
      </template>
    </UclDetailPageComponent>

    <UclDetailPageExternalReference :data="externalReferences" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-icons {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  width: 100%;
}

.ucl-icons__hint {
  margin: 0;
  color: var(--font-color-dimmed);
}

.ucl-icons__count {
  font-family: var(--font-family-monospace);
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}

.ucl-icons__emblems {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  padding: var(--dimension-5);
  border: 1px solid var(--default-border-color);
  border-radius: var(--dimension-3);
}

.ucl-icons__emblems-title {
  font-weight: var(--font-weight-bold);
}

.ucl-icons__emblems-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(72px, 1fr));
  gap: var(--dimension-3);
}

.ucl-icons__emblem-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--dimension-4);
  padding: var(--dimension-4) var(--dimension-3) var(--dimension-6);
  border: 1px solid var(--default-border-color);
  border-radius: var(--dimension-3);
  background: var(--default-form-element-bg-color);
  color: var(--font-color);
  cursor: pointer;
  outline: 2px solid transparent;
  outline-offset: 1px;
  transition: outline-color 120ms ease;
}

.ucl-icons__emblem-card:hover,
.ucl-icons__emblem-card:focus-visible {
  outline-color: var(--success);
}

.ucl-icons__emblem-card--picked {
  border-color: var(--success);
}

.ucl-icons__emblem-base {
  display: block;
  width: 32px;
  height: 32px;
  border: 1px dashed var(--default-border-color);
  border-radius: var(--dimension-2);
}

.ucl-icons__grid {
  display: grid;
  grid-template-columns: repeat(
    auto-fill,
    minmax(max(120px, calc(var(--ucl-icons-preview-size, 40px) + var(--dimension-7))), 1fr)
  );
  gap: var(--dimension-4);
}

.ucl-icons__card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-4) var(--dimension-3);
  border: 1px solid var(--default-border-color);
  border-radius: var(--dimension-3);
  background: var(--default-form-element-bg-color);
  color: var(--font-color);
  cursor: pointer;
  transition: outline-color 120ms ease;
  outline: 2px solid transparent;
  outline-offset: 1px;
}

.ucl-icons__card:hover,
.ucl-icons__card:focus-visible {
  outline-color: var(--success);
}

.ucl-icons__preview {
  display: flex;
  align-items: center;
  justify-content: center;
  height: max(40px, var(--ucl-icons-preview-size, 40px));
}

.ucl-icons__preview--emblem {
  padding-bottom: calc(0.2 * var(--ucl-icons-preview-size, 40px));
}

.ucl-icons__name {
  font-family: var(--font-family-monospace);
  font-size: var(--font-size-small);
  text-align: center;
  overflow-wrap: anywhere;
  line-height: 1.2;
}

.ucl-icons__meta {
  display: flex;
  align-items: center;
  gap: var(--dimension-2);
}

.ucl-icons__badge {
  font-family: var(--font-family-monospace);
  font-size: 10px;
  font-weight: var(--font-weight-bold);
  padding: 1px var(--dimension-2);
  border-radius: var(--dimension-2);
  border: 1px solid var(--default-border-color);
  color: var(--font-color-dimmed);
}

.ucl-icons__badge--svg {
  color: var(--success);
  border-color: var(--success);
}

.ucl-icons__badge--multitone {
  color: var(--color-light-blue-60);
  border-color: var(--color-light-blue-60);
}

.ucl-icons__badge--themed {
  color: var(--color-purple-60);
  border-color: var(--color-purple-60);
}

.ucl-icons__empty {
  margin: 0;
  color: var(--font-color-dimmed);
}

.ucl-icons__popover {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  min-width: 240px;
  padding: var(--dimension-3);
  background: var(--default-bg-color);
  border: 1px solid var(--default-border-color);
  border-radius: var(--dimension-3);
  box-shadow: var(--dropdown-list-box-shadow);
  z-index: var(--z-index-tooltip-offset);
}

.ucl-icons__popover-head {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-2) var(--dimension-3);
}

.ucl-icons__popover-name {
  font-family: var(--font-family-monospace);
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}

.ucl-icons__copy-option {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--dimension-4);
  width: 100%;
  padding: var(--dimension-3) var(--dimension-4);
  border: 1px solid transparent;
  border-radius: var(--dimension-3);
  background: transparent;
  color: var(--font-color);
  font-family: var(--font-family-monospace);
  font-size: var(--font-size-small);
  cursor: pointer;
  text-align: left;
}

.ucl-icons__copy-option:hover,
.ucl-icons__copy-option:focus-visible {
  background: var(--default-form-element-bg-color);
  border-color: var(--success);
  outline: none;
}

.ucl-icons__copy-label {
  font-weight: var(--font-weight-bold);
  color: var(--font-color-dimmed);
  flex: 0 0 auto;
}

.ucl-icons__copy-value {
  flex: 1 1 auto;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
