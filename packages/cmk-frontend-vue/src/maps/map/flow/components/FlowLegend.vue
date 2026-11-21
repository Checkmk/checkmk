<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What the shapes, rings and lines of a flow map mean. The map encodes most of it
in colour and stroke alone, which nothing else on the page explains.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, useId } from 'vue'

import MapOverlayButton from '@/maps/map/components/MapOverlayButton.vue'

const { _t } = usei18n()

const open = ref(false)
const panelId = useId()
const SAMPLE_COUNT = 3

type Swatch = 'site' | 'host' | 'group' | 'badge' | 'frame' | 'line'

interface Entry {
  swatch: Swatch
  variant: string
  text: string
}

const sections = computed<{ title: string; entries: Entry[] }[]>(() => [
  {
    title: _t('Nodes'),
    entries: [
      {
        swatch: 'site',
        variant: 'site',
        text: _t('Site; outlined in the colour of its worst problem')
      },
      { swatch: 'host', variant: 'plain', text: _t('Host, in the colour of its state') },
      { swatch: 'host', variant: 'quiet', text: _t('Grey host: up, while only problems show') },
      { swatch: 'group', variant: 'group', text: _t('Group of hosts folded under their parent') },
      { swatch: 'frame', variant: 'frame', text: _t('Opened group; its − button folds it again') }
    ]
  },
  {
    title: _t('Rings and badges'),
    entries: [
      { swatch: 'host', variant: 'ring', text: _t("Host ring: its services' worst state") },
      { swatch: 'host', variant: 'thick', text: _t('Thick ring: one of the hosts worst affected') },
      {
        swatch: 'host',
        variant: 'worst',
        text: _t('Glowing: down, and others unreachable because of it')
      },
      {
        swatch: 'group',
        variant: 'group-ring',
        text: _t("Group ring: its hosts' states, handled problems grey")
      },
      {
        swatch: 'badge',
        variant: 'badge',
        text: _t('Group number: its hosts that need attention, or else those unreachable')
      }
    ]
  },
  {
    title: _t('Lines'),
    entries: [
      { swatch: 'line', variant: 'child', text: _t("To a child host, in its parent's state") },
      { swatch: 'line', variant: 'site', text: _t('From a site to its hosts') },
      {
        swatch: 'line',
        variant: 'further',
        text: _t('To a further parent, or past hosts left out')
      }
    ]
  }
])
</script>

<template>
  <div class="maps-flow-legend" @keydown.escape="open = false">
    <!-- Pointer-only dismissal, as the service picker's; Escape is the keyboard path. -->
    <div v-if="open" class="maps-flow-legend__backdrop" aria-hidden="true" @click="open = false" />
    <div
      v-if="open"
      :id="panelId"
      class="maps-flow-legend__panel"
      role="region"
      :aria-label="_t('Legend')"
    >
      <section v-for="section in sections" :key="section.title" class="maps-flow-legend__section">
        <h3 class="maps-flow-legend__title">{{ section.title }}</h3>
        <ul class="maps-flow-legend__entries">
          <li v-for="entry in section.entries" :key="entry.variant" class="maps-flow-legend__entry">
            <svg class="maps-flow-legend__swatch" viewBox="0 0 24 24" aria-hidden="true">
              <rect
                v-if="entry.swatch === 'site'"
                x="1"
                y="6"
                width="22"
                height="12"
                rx="3"
                class="maps-flow-legend__site"
              />
              <circle
                v-else-if="entry.swatch === 'host'"
                cx="12"
                cy="12"
                r="7"
                class="maps-flow-legend__host"
                :class="`maps-flow-legend__host--${entry.variant}`"
              />
              <template v-else-if="entry.swatch === 'group'">
                <circle cx="12" cy="12" r="4" class="maps-flow-legend__group-edge" />
                <circle cx="12" cy="12" r="7" class="maps-flow-legend__group" />
                <circle
                  cx="12"
                  cy="12"
                  r="7"
                  class="maps-flow-legend__group maps-flow-legend__group--problems"
                />
              </template>
              <g v-else-if="entry.swatch === 'badge'">
                <circle cx="12" cy="12" r="8" class="maps-flow-legend__badge" />
                <text x="12" y="12" class="maps-flow-legend__badge-count">{{ SAMPLE_COUNT }}</text>
              </g>
              <rect
                v-else-if="entry.swatch === 'frame'"
                x="2"
                y="3"
                width="20"
                height="18"
                rx="2"
                class="maps-flow-legend__frame"
              />
              <template v-else>
                <line
                  x1="2"
                  y1="12"
                  x2="22"
                  y2="12"
                  class="maps-flow-legend__line"
                  :class="`maps-flow-legend__line--${entry.variant}`"
                />
              </template>
            </svg>
            <span>{{ entry.text }}</span>
          </li>
        </ul>
      </section>
      <p class="maps-flow-legend__keys">
        {{ _t('Arrow keys move along the tree, Enter opens a group, Escape folds it.') }}
      </p>
    </div>
    <MapOverlayButton
      class="maps-flow-legend__button"
      :expanded="open"
      :aria-controls="panelId"
      @click="open = !open"
    >
      {{ _t('Legend') }}
    </MapOverlayButton>
  </div>
</template>

<style scoped>
.maps-flow-legend__backdrop {
  position: fixed;
  inset: 0;
}

.maps-flow-legend__button,
.maps-flow-legend__panel {
  position: relative;
}

/* As high as the service layout picker beside it. */
.maps-flow-legend__button {
  padding: var(--dimension-3) var(--dimension-5);
  line-height: 16px;
  box-shadow: var(--maps-shadow-canvas-overlay-high);
}

.maps-flow-legend__button:focus-visible {
  outline: revert;
}

.maps-flow-legend__panel {
  position: absolute;
  right: 0;
  bottom: 100%;

  /* Over the map's corner rather than its own button, so it stays within the
     map that a small window or a large zoom leaves small: the corner is
     ``--dimension-8`` in from the map's edges, its button as high as its line
     and padding, and the panel as high as its own padding besides. */
  width: min(300px, calc(100cqw - 2 * var(--dimension-8) - 2 * var(--dimension-5)));
  max-height: calc(
    100cqh - 2 * var(--dimension-8) - 3 * var(--dimension-4) - 16px - 2 * var(--dimension-3)
  );
  overflow-y: auto;
  margin-bottom: var(--dimension-4);
  padding: var(--dimension-4) var(--dimension-5);
  background: var(--ux-theme-3);
  border-radius: var(--border-radius);
  box-shadow:
    0 0 0 1px var(--default-border-color),
    var(--maps-shadow-canvas-overlay-high);
}

.maps-flow-legend__section + .maps-flow-legend__section {
  margin-top: var(--dimension-4);
}

.maps-flow-legend__title {
  margin: 0 0 var(--dimension-2);
  color: var(--font-color-dimmed);
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-semibold);
}

.maps-flow-legend__entries {
  margin: 0;
  padding: 0;
  list-style: none;
}

.maps-flow-legend__entry {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  padding: var(--dimension-2) 0;
  color: var(--font-color);
  font-size: var(--font-size-normal);
}

.maps-flow-legend__swatch {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
}

/* The site box and its outline are those ``paint`` draws. */
.maps-flow-legend__site {
  fill: var(--ux-theme-4);
  stroke: var(--color-state-critical);
  stroke-width: 1.5;
}

/* The ring widths are those of a host's halo in ``nodeModel``. */
.maps-flow-legend__host {
  fill: var(--color-state-ok);
  stroke: var(--color-state-critical);
}

.maps-flow-legend__host--plain {
  stroke: none;
}

.maps-flow-legend__host--quiet {
  fill: var(--font-color-dimmed);
  stroke-width: 2.5;
}

.maps-flow-legend__keys {
  margin: var(--dimension-4) 0 0;
  color: var(--font-color-dimmed);
  font-size: var(--font-size-normal);
}

.maps-flow-legend__host--ring {
  stroke-width: 2.5;
}

.maps-flow-legend__host--thick {
  stroke-width: 4;
}

.maps-flow-legend__host--worst {
  fill: var(--color-state-critical);
  stroke: none;
  filter: drop-shadow(0 0 3px var(--color-state-critical));
}

.maps-flow-legend__group {
  fill: none;
  stroke: var(--color-state-ok);
  stroke-width: 2.5;
}

/* The dashed edge inside a group's ring, as the map draws it. */
.maps-flow-legend__group-edge {
  fill: none;
  stroke: var(--font-color-dimmed);
  stroke-width: 1;
  stroke-dasharray: 2 1.5;
}

/* A quarter of the ring, which is 2π·7 long, in trouble. */
.maps-flow-legend__group--problems {
  stroke: var(--color-state-critical);
  stroke-dasharray: 11 33;
}

.maps-flow-legend__frame {
  fill: none;
  stroke: var(--interactive-accent);
  stroke-width: 1;
  stroke-dasharray: 3 2;
}

.maps-flow-legend__badge {
  fill: var(--color-state-critical);
}

.maps-flow-legend__badge-count {
  fill: var(--white);
  font-size: 10px;
  font-weight: var(--font-weight-bold);
  text-anchor: middle;
  dominant-baseline: central;
}

.maps-flow-legend__line {
  stroke-width: 1.5;
}

.maps-flow-legend__line--child {
  stroke: var(--color-state-ok);
}

.maps-flow-legend__line--site {
  stroke: var(--font-color-dimmed);
  stroke-width: 1;
  stroke-dasharray: 2 3;
}

.maps-flow-legend__line--further {
  stroke: var(--color-state-ok);
  stroke-width: 1;
  stroke-dasharray: 6 4;
}
</style>
