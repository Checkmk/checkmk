<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import { type PanelState } from '@ucl/_ucl/types/prop-panel'

export const panelConfig = {
  filter: {
    type: 'string' as const,
    title: 'Search',
    initialState: '',
    help: 'Substring match against token name (e.g. green, mid-grey-50).'
  }
} satisfies PanelConfig & PanelConfigFor<unknown>
</script>

<script setup lang="ts">
import {
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import { PopoverContent, PopoverPortal, PopoverRoot, PopoverTrigger } from 'reka-ui'
import { computed, nextTick, onMounted, ref } from 'vue'

import CmkCopy from '@/components/CmkCopy.vue'

defineProps<{ screenshotMode: boolean }>()

const FAMILIES = [
  'corporate-green',
  'light-blue',
  'dark-blue',
  'yellow',
  'light-red',
  'dark-red',
  'orange',
  'brown',
  'pink',
  'purple',
  'cyan',
  'dark-green',
  'digital-green',
  'conference-grey',
  'daylight-grey',
  'mid-grey',
  'midnight-grey',
  'mist-grey',
  'white'
] as const
type Family = (typeof FAMILIES)[number]

const SHADES = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100] as const
type Shade = (typeof SHADES)[number]

type Swatch = {
  token: string
  shade: Shade
  hex: string
  rgb: string
  rgbFn: 'rgb' | 'rgba'
}
type FamilyRow = { name: Family; swatches: Swatch[] }

const palette = ref<FamilyRow[]>([])
const swatchEls = new Map<string, HTMLElement>()

function setSwatchRef(token: string, el: unknown): void {
  if (el instanceof HTMLElement) {
    swatchEls.set(token, el)
  } else {
    swatchEls.delete(token)
  }
}

function formatColor(bg: string): { hex: string; rgb: string; rgbFn: 'rgb' | 'rgba' } | null {
  // getComputedStyle returns canonical "rgb(r, g, b)" or "rgba(r, g, b, a)".
  const match = bg.match(
    /^rgba?\(\s*([\d.]+)\s*,?\s*([\d.]+)\s*,?\s*([\d.]+)(?:\s*[,/]\s*([\d.]+%?))?\s*\)$/i
  )
  if (!match || match[1] === undefined || match[2] === undefined || match[3] === undefined) {
    return null
  }
  const r = Math.round(parseFloat(match[1]))
  const g = Math.round(parseFloat(match[2]))
  const b = Math.round(parseFloat(match[3]))
  const alpha =
    match[4] === undefined
      ? 1
      : match[4].endsWith('%')
        ? parseFloat(match[4]) / 100
        : parseFloat(match[4])
  const toHex = (n: number) => n.toString(16).padStart(2, '0').toUpperCase()
  if (alpha < 1) {
    return {
      hex: `#${toHex(r)}${toHex(g)}${toHex(b)}${toHex(Math.round(alpha * 255))}`,
      rgb: `${r}, ${g}, ${b}, ${alpha.toFixed(2).replace(/\.?0+$/, '')}`,
      rgbFn: 'rgba'
    }
  }
  return {
    hex: `#${toHex(r)}${toHex(g)}${toHex(b)}`,
    rgb: `${r}, ${g}, ${b}`,
    rgbFn: 'rgb'
  }
}

onMounted(async () => {
  const rootStyle = getComputedStyle(document.documentElement)
  palette.value = FAMILIES.map((family) => ({
    name: family,
    swatches: SHADES.map((shade) => {
      const token = `--color-${family}-${shade}`
      const value = rootStyle.getPropertyValue(token).trim()
      return { token, value, shade }
    })
      .filter((s) => s.value !== '' && CSS.supports('background-color', s.value))
      .map(({ token, shade }): Swatch => ({ token, shade, hex: '', rgb: '', rgbFn: 'rgb' }))
  })).filter((row) => row.swatches.length > 0)

  // After swatches render, read the canonical computed background-color from
  // each rendered button so we automatically handle alpha (e.g. white-N).
  await nextTick()
  for (const row of palette.value) {
    for (const swatch of row.swatches) {
      const el = swatchEls.get(swatch.token)
      if (!el) {
        continue
      }
      const parsed = formatColor(getComputedStyle(el).backgroundColor)
      if (parsed) {
        swatch.hex = parsed.hex
        swatch.rgb = parsed.rgb
        swatch.rgbFn = parsed.rgbFn
      }
    }
  }
})

const propState = ref<PanelState>({ filter: panelConfig.filter.initialState })

const filtered = computed(() => {
  const needle = (propState.value['filter'] as string).trim().toLowerCase()
  if (!needle) {
    return palette.value
  }
  return palette.value
    .map((row) => ({
      name: row.name,
      swatches: row.swatches.filter((s) => s.token.includes(needle) || row.name.includes(needle))
    }))
    .filter((row) => row.swatches.length > 0)
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>Colors</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-colors">
        <p class="ucl-colors__hint">
          Documented <code>--color-*</code> tokens declared on <code>:root</code>. Values are read
          live from the page, so this view reflects the currently loaded theme. Click a swatch to
          choose between copying its <code>var(--color-…)</code>, hex, or <code>rgb()</code>/<code
            >rgba()</code
          >
          string.
        </p>

        <div v-for="row in filtered" :key="row.name" class="ucl-colors__family">
          <div class="ucl-colors__family-name">{{ row.name }}</div>
          <div class="ucl-colors__swatches">
            <PopoverRoot v-for="swatch in row.swatches" :key="swatch.token">
              <PopoverTrigger as-child>
                <button
                  :ref="(el) => setSwatchRef(swatch.token, el)"
                  type="button"
                  class="ucl-colors__swatch"
                  :title="`${swatch.token}\n${swatch.hex} ${swatch.rgbFn}(${swatch.rgb})`"
                  :style="{ background: `var(${swatch.token})` }"
                >
                  <span class="ucl-colors__swatch-shade">{{ swatch.shade }}</span>
                  <span class="ucl-colors__swatch-values">
                    <span class="ucl-colors__swatch-hex">{{ swatch.hex }}</span>
                    <span class="ucl-colors__swatch-rgb">{{ swatch.rgb }}</span>
                  </span>
                </button>
              </PopoverTrigger>
              <PopoverPortal>
                <PopoverContent side="top" align="center" :side-offset="6" as-child>
                  <div class="ucl-colors__popover">
                    <div class="ucl-colors__popover-token">{{ swatch.token }}</div>
                    <CmkCopy :text="`var(${swatch.token})`">
                      <button type="button" class="ucl-colors__copy-option">
                        <span class="ucl-colors__copy-label">var()</span>
                        <span class="ucl-colors__copy-value">var({{ swatch.token }})</span>
                      </button>
                    </CmkCopy>
                    <CmkCopy :text="swatch.hex">
                      <button type="button" class="ucl-colors__copy-option">
                        <span class="ucl-colors__copy-label">hex</span>
                        <span class="ucl-colors__copy-value">{{ swatch.hex }}</span>
                      </button>
                    </CmkCopy>
                    <CmkCopy :text="`${swatch.rgbFn}(${swatch.rgb})`">
                      <button type="button" class="ucl-colors__copy-option">
                        <span class="ucl-colors__copy-label">{{ swatch.rgbFn }}</span>
                        <span class="ucl-colors__copy-value"
                          >{{ swatch.rgbFn }}({{ swatch.rgb }})</span
                        >
                      </button>
                    </CmkCopy>
                  </div>
                </PopoverContent>
              </PopoverPortal>
            </PopoverRoot>
          </div>
        </div>

        <p v-if="filtered.length === 0" class="ucl-colors__empty">
          No tokens match "{{ propState['filter'] }}".
        </p>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" title="Filters" />
      </template>
    </UclDetailPageComponent>
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-colors {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
  width: 100%;
}

.ucl-colors__hint {
  margin: 0;
  color: var(--font-color-dimmed);
}

.ucl-colors__family {
  display: grid;
  grid-template-columns: 140px 1fr;
  align-items: center;
  gap: var(--dimension-5);
}

.ucl-colors__family-name {
  font-family: var(--font-family-monospace);
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}

.ucl-colors__swatches {
  display: grid;
  grid-template-columns: repeat(11, minmax(80px, 1fr));
  gap: var(--dimension-3);
}

.ucl-colors__swatch {
  aspect-ratio: 4 / 5;
  width: 100%;
  border: 1px solid var(--default-border-color);
  border-radius: var(--dimension-3);
  padding: 0;
  position: relative;
  cursor: pointer;
  font-family: var(--font-family-monospace);
  font-size: var(--font-size-small);
  color: var(--font-color);
  transition: outline-color 120ms ease;
  outline: 2px solid transparent;
  outline-offset: 1px;
}

.ucl-colors__swatch:hover,
.ucl-colors__swatch:focus-visible {
  outline-color: var(--success);
}

.ucl-colors__swatch-shade {
  position: absolute;
  inset: var(--dimension-3) var(--dimension-3) auto auto;
  pointer-events: none;
  mix-blend-mode: difference;
  color: var(--white);
}

.ucl-colors__swatch-values {
  position: absolute;
  inset: auto var(--dimension-3) var(--dimension-3) var(--dimension-3);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
  pointer-events: none;
  mix-blend-mode: difference;
  color: var(--white);
  font-size: 10px;
  line-height: 1.1;
  text-align: left;
}

.ucl-colors__swatch-hex {
  font-weight: var(--font-weight-bold);
}

.ucl-colors__swatch-rgb {
  opacity: 0.85;
}

.ucl-colors__empty {
  margin: 0;
  color: var(--font-color-dimmed);
}

.ucl-colors__popover {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  min-width: 220px;
  padding: var(--dimension-3);
  background: var(--default-bg-color);
  border: 1px solid var(--default-border-color);
  border-radius: var(--dimension-3);
  box-shadow: var(--dropdown-list-box-shadow);
  z-index: var(--z-index-tooltip-offset);
}

.ucl-colors__popover-token {
  font-family: var(--font-family-monospace);
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
  padding: var(--dimension-2) var(--dimension-3);
}

.ucl-colors__copy-option {
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

.ucl-colors__copy-option:hover,
.ucl-colors__copy-option:focus-visible {
  background: var(--default-form-element-bg-color);
  border-color: var(--success);
  outline: none;
}

.ucl-colors__copy-label {
  font-weight: var(--font-weight-bold);
  color: var(--font-color-dimmed);
  flex: 0 0 auto;
}

.ucl-colors__copy-value {
  flex: 1 1 auto;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
