/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, within } from '@testing-library/vue'
import { nextTick } from 'vue'

import HostRelationsSection from '@/monitoring/all-hosts/components/slide-in/HostRelationsSection.vue'
import type { HostOverview } from '@/monitoring/shared/api/types'

type Relation = HostOverview['relations'][number]
type RelationHealth = NonNullable<Relation['health']>

const HEALTHY: RelationHealth = {
  state: 'UP',
  service_counts: { ok: 4, warn: 0, crit: 0, unknown: 0, pending: 0, total: 4 }
}

function makeRelation(overrides: Partial<Relation> = {}): Relation {
  return {
    host_name: 'mgmt-web-1',
    kind: 'management',
    direction: 'parent',
    relation_type: 'Management board',
    site_id: 'local',
    health: HEALTHY,
    ...overrides
  }
}

function renderSection(
  props: { relations?: Relation[]; moreRelations?: boolean; revealRequest?: number } = {}
) {
  return render(HostRelationsSection, {
    props: { relations: props.relations ?? [], ...props }
  })
}

test('tells the user when the host has no relations', () => {
  renderSection()

  expect(screen.getByText('No relations set')).toBeInTheDocument()
})

/** The card of one related host, found by the heading naming it. */
function cardOf(hostName: string): HTMLElement {
  const card = screen.getByRole('heading', { name: hostName }).closest('li')
  if (card === null) {
    throw new Error(`No card for ${hostName}`)
  }
  return card
}

test('names the relation type on every related host', () => {
  renderSection({
    relations: [
      makeRelation(),
      makeRelation({
        host_name: 'os-web-1',
        direction: 'child',
        relation_type: 'OS host',
        health: { ...HEALTHY, state: 'DOWN' }
      })
    ]
  })

  expect(screen.queryByText('No relations set')).not.toBeInTheDocument()
  expect(
    within(cardOf('mgmt-web-1')).getByText('Relation type: Management board')
  ).toBeInTheDocument()
  expect(within(cardOf('os-web-1')).getByText('Relation type: OS host')).toBeInTheDocument()
})

test('points the service counts of a related host at its services', () => {
  renderSection({ relations: [makeRelation()] })

  expect(screen.getByRole('link', { name: 'All services: 4' }).getAttribute('href')).toContain(
    'monitor_host_services.py?host=mgmt-web-1&site=local'
  )
})

test('leaves the card itself unlinked', () => {
  renderSection({ relations: [makeRelation()] })

  expect(cardOf('mgmt-web-1').querySelector('a.cmk-link-card')).toBeNull()
})

test('counts the services of every related host without asking the reader to open it', () => {
  renderSection({ relations: [makeRelation()] })

  const card = within(cardOf('mgmt-web-1'))
  expect(card.getByText('All services: 4')).toBeInTheDocument()
  expect(card.getByText('OK: 4')).toBeInTheDocument()
})

test('keeps the service bar of a related host slimmer than the one of the host itself', () => {
  renderSection({ relations: [makeRelation()] })

  expect(cardOf('mgmt-web-1').querySelector('.cmk-state-count-bar--size-small')).not.toBeNull()
})

test('does not claim a cut list when the host has no relations to show at all', () => {
  // Everything the host is related to was left out, so there is nothing the notice could add to.
  renderSection({ relations: [], moreRelations: true })

  expect(screen.getByText('No relations set')).toBeInTheDocument()
  expect(screen.queryByText(/related to more hosts/)).not.toBeInTheDocument()
})

test('says so when the server cut the list of related hosts', () => {
  renderSection({ relations: [makeRelation()], moreRelations: true })

  expect(screen.getByText(/related to more hosts than the 1 listed here/)).toBeInTheDocument()
})

test('does not claim a cut list when every related host is there', () => {
  renderSection({ relations: [makeRelation()] })

  expect(screen.queryByText(/related to more hosts/)).not.toBeInTheDocument()
})

test('keeps a related host whose site is unavailable, saying so instead of counting', () => {
  renderSection({ relations: [makeRelation({ health: null })] })

  expect(screen.getByText('mgmt-web-1')).toBeInTheDocument()
  expect(screen.getByText('UNKNOWN')).toBeInTheDocument()
  expect(screen.getByText(/Site local is not available/)).toBeInTheDocument()
  expect(screen.queryByText('OK: 4')).not.toBeInTheDocument()
})

test('reveals the related hosts beyond the preview limit on demand', async () => {
  const relations = Array.from({ length: 7 }, (_, index) =>
    makeRelation({ host_name: `mgmt-web-${index}` })
  )
  renderSection({ relations })

  expect(screen.getByText('mgmt-web-4')).toBeInTheDocument()
  expect(screen.queryByText('mgmt-web-5')).not.toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: 'Show 2 more hosts' }))

  expect(screen.getByText('mgmt-web-6')).toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: 'Show fewer' }))

  expect(screen.queryByText('mgmt-web-6')).not.toBeInTheDocument()
})

test('lists every related host when there are no more than the preview limit', () => {
  const relations = Array.from({ length: 5 }, (_, index) =>
    makeRelation({ host_name: `mgmt-web-${index}` })
  )
  renderSection({ relations })

  expect(screen.getByText('mgmt-web-4')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Show/ })).not.toBeInTheDocument()
})

function sectionOf(container: Element): Element | null {
  return container.querySelector('.monitoring-host-relations-section')
}

test('takes the reader to the relations of the host the tab already shows', async () => {
  // The panel keeps the same tab when the reader clicks the relation count of the host on show,
  // so nothing remounts and the reveal arrives as a changed prop.
  const relations = [makeRelation()]

  const { container, rerender } = renderSection({ relations, revealRequest: 0 })
  await nextTick()
  expect(document.activeElement).not.toBe(sectionOf(container))

  await rerender({ relations, revealRequest: 1 })
  await nextTick()

  expect(document.activeElement).toBe(sectionOf(container))
})

test('takes the reader there again when they ask for the same relations twice', async () => {
  // Scrolled away and clicked the same relation count again: a flag would already be set, so the
  // ask has to be counted for the panel to move at all.
  const relations = [makeRelation()]

  const { container, rerender } = renderSection({ relations, revealRequest: 1 })
  await nextTick()
  expect(document.activeElement).toBe(sectionOf(container))
  ;(document.activeElement as HTMLElement).blur()

  await rerender({ relations, revealRequest: 2 })
  await nextTick()

  expect(document.activeElement).toBe(sectionOf(container))
})

test('leaves the reader at the top of the tab when it was not opened for the relations', async () => {
  const { container } = renderSection({ relations: [makeRelation()] })
  await nextTick()

  expect(document.activeElement).not.toBe(sectionOf(container))
})
