/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, markRaw } from 'vue'

import { useObjectHoverMenu } from '@/maps/map/composables/useObjectHoverMenu'
import FolderTreeMapView from '@/maps/map/foldertree/FolderTreeMapView.vue'
import { HOVER_REST_MS } from '@/maps/map/foldertree/composables/useTileHoverIntent'
import type { FolderHostService, FolderServiceSearchResult, FolderTreeNode } from '@/maps/types/api'

import { aFolderNode, aMap, newMapView } from '../../support/fixtures'
import { fakeMapsServices, provideServices } from '../../support/services'

/** A fetched service, as the daemon hands it over. */
const aService = (name: string): FolderHostService => ({
  name,
  state: 'OK',
  output: '',
  acknowledged: false,
  in_downtime: false,
  is_flapping: false
})

/** Longer than the search debounce, so a needle has reached the server. */
const AFTER_THE_DEBOUNCE_MS = 400

// Root folder with one healthy and one problem host.
const sampleTree = (): FolderTreeNode =>
  aFolderNode({
    path: '/main',
    title: 'Main',
    kind: 'folder',
    host_count: 2,
    problem_count: 1,
    severity_counts: { DOWN: 1 },
    state: 'DOWN',
    children: [
      aFolderNode({ path: '/main/web-01', title: 'web-01', kind: 'host', state: 'UP' }),
      aFolderNode({
        path: '/main/db-01',
        title: 'db-01',
        kind: 'host',
        state: 'DOWN',
        output: 'PING CRITICAL'
      })
    ]
  })

/**
 * The map view owns the hover card and hands it down, so the case builds a real
 * one in a host component -- the app-level provide is what makes its own
 * injections resolve.
 */
const hostComponent = defineComponent({
  components: { FolderTreeMapView },
  props: {
    config: { type: Object, required: false, default: null },
    needle: { type: String, default: '' }
  },
  setup() {
    return { hover: useObjectHoverMenu() }
  },
  template: `<FolderTreeMapView
    :config="config"
    :error="null"
    :preview="false"
    :kiosk="false"
    :checkmk-url="null"
    :filter-needle="needle"
    :hover="hover"
  />`
})

/** The map a folder tree draws, named so a case can swap one for another. */
function aFolderTreeMap(name: string, showServices: boolean, drawing: 'list' | 'map' = 'list') {
  return aMap({
    name,
    view: { ...newMapView('foldertree'), default_view: drawing, show_services: showServices }
  })
}

function renderTree(
  options: {
    withTree?: boolean
    showServices?: boolean
    tree?: FolderTreeNode
    drawing?: 'list' | 'map'
  } = {}
) {
  const services = fakeMapsServices()
  const config = aFolderTreeMap('map1', options.showServices ?? false, options.drawing)
  services.maps.currentMap.value = config
  if (options.withTree !== false) {
    services.states.folderTree.value = markRaw(options.tree ?? sampleTree())
    services.states.connected.value = true
  }
  const { global: provided } = provideServices(services)
  return {
    services,
    config,
    ...render(hostComponent, {
      props: { config },
      global: { ...provided, stubs: { MapSearch: true } }
    })
  }
}

async function waitForRows() {
  await waitFor(() => expect(screen.getAllByRole('treeitem')).toHaveLength(3))
}

describe('FolderTreeMapView (list mode)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      }
    )
    // jsdom has no layout, so the windowed list would measure a 0px viewport.
    // A fixed clientHeight gives the windowing something real to work from.
    Object.defineProperty(HTMLElement.prototype, 'clientHeight', {
      configurable: true,
      get: () => 800
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    Reflect.deleteProperty(HTMLElement.prototype, 'clientHeight')
  })

  it('renders the root folder and both host rows in the virtual window', async () => {
    const { container } = renderTree()
    await waitForRows()

    const rows = screen.getAllByRole('treeitem')
    expect(rows[0]).toHaveTextContent('Main')
    expect(rows[1]).toHaveTextContent('web-01')
    expect(rows[2]).toHaveTextContent('db-01')
    // Geometry: the full-height spacer drives the scrollbar (3 rows × 28px);
    // pure windowing arithmetic with no accessible representation.
    expect(
      container.querySelector('.maps-folder-tree-list__spacer')?.getAttribute('style')
    ).toContain('height: 84px')
  })

  it('marks the problem host and shows the severity pill on the folder', async () => {
    renderTree()
    await waitForRows()

    // The state dot's translated tooltip is its accessible surface.
    const down = screen.getByTitle('Down')
    expect(down.closest('[role="treeitem"]')).toHaveTextContent('db-01')

    // Pills carry their meaning in the translated tooltip.
    expect(screen.getByTitle('1 Down host')).toHaveTextContent('1')
  })

  it('shows the host summary in the toolbar and the List mode as selected', async () => {
    renderTree()
    await waitForRows()

    // "2 hosts" also appears in the folder row's meta; the toolbar summary is
    // the occurrence outside the tree rows.
    const summaries = screen.getAllByText(/2 hosts/)
    expect(summaries.some((element) => element.closest('[role="treeitem"]') === null)).toBe(true)
    expect(screen.getByText('1 Down')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Toggle List', pressed: true })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Toggle Map', pressed: false })).toBeInTheDocument()
  })

  it('does not call an empty search result all OK', async () => {
    const { rerender } = renderTree()
    await waitForRows()

    await rerender({ needle: 'h:nothing-is-called-this' })

    expect(await screen.findByText('showing 0 hosts')).toBeInTheDocument()
    expect(screen.queryByText(/all OK/)).toBeNull()
  })

  it('renders the waiting placeholder when no folder tree arrived yet', () => {
    renderTree({ withTree: false })

    expect(screen.getByText(/Waiting for folder data/)).toBeInTheDocument()
    expect(screen.queryAllByRole('treeitem')).toHaveLength(0)
  })

  it('collapses the folder via keyboard: focus the chevron, press Enter', async () => {
    const user = userEvent.setup()
    renderTree()
    await waitForRows()

    const chevron = screen.getByRole('button', { name: 'Collapse' })
    chevron.focus()
    await user.keyboard('{Enter}')

    await waitFor(() => expect(screen.getAllByRole('treeitem')).toHaveLength(1))
    expect(screen.getByRole('treeitem')).toHaveTextContent('Main')
    expect(screen.getByRole('button', { name: 'Expand' })).toBeInTheDocument()
  })

  it('is one tab stop, and the arrow keys walk the rows, up to the parent and shut', async () => {
    const user = userEvent.setup()
    renderTree()
    await waitForRows()
    const [main, first, second] = screen.getAllByRole('treeitem')
    expect([main, first, second].map((row) => row!.tabIndex)).toEqual([0, -1, -1])

    main!.focus()
    await user.keyboard('{ArrowDown}')
    expect(first).toHaveFocus()
    await user.keyboard('{ArrowLeft}')
    expect(main).toHaveFocus()
    await user.keyboard('{ArrowLeft}')

    await waitFor(() => expect(screen.getAllByRole('treeitem')).toHaveLength(1))
  })

  it('keeps the focus on an open row whose only child is a note', async () => {
    const user = userEvent.setup()
    renderTree({ showServices: true })
    await waitForRows()
    const web = screen.getByRole('treeitem', { name: /web-01/ })

    web.focus()
    await user.keyboard('{ArrowRight}')
    await screen.findByText('No services')
    await user.keyboard('{ArrowRight}')

    expect(web).toHaveFocus()
  })

  it('leaves the arrow keys with a modifier to the browser', async () => {
    renderTree()
    await waitForRows()
    const [main] = screen.getAllByRole('treeitem')

    const back = new KeyboardEvent('keydown', {
      key: 'ArrowLeft',
      altKey: true,
      bubbles: true,
      cancelable: true
    })
    main!.dispatchEvent(back)

    expect(back.defaultPrevented).toBe(false)
  })

  it('keeps the tree in the tab order after the focused row is scrolled away', async () => {
    renderTree({
      tree: aFolderNode({
        path: '/main',
        title: 'Main',
        kind: 'folder',
        host_count: 100,
        children: Array.from({ length: 100 }, (_, index) =>
          aFolderNode({ path: `/main/host-${index}`, title: `host-${index}`, kind: 'host' })
        )
      })
    })
    await screen.findAllByRole('treeitem')
    const tree = screen.getByRole('tree')

    tree.scrollTop = 2000
    await fireEvent.scroll(tree)

    await waitFor(() =>
      expect(screen.getAllByRole('treeitem').some((row) => row.tabIndex === 0)).toBe(true)
    )
    expect(screen.queryByRole('treeitem', { name: /Main/ })).toBeNull()
  })

  it('expands a host from its chevron by keyboard rather than opening the leaf', async () => {
    const user = userEvent.setup()
    renderTree({ showServices: true })
    await waitForRows()

    // Main is open, so the two Expand chevrons are the hosts'.
    const [webChevron] = screen.getAllByRole('button', { name: 'Expand' })
    webChevron!.focus()
    await user.keyboard('{Enter}')

    await waitFor(() =>
      expect(screen.getByRole('treeitem', { name: /web-01/ })).toHaveAttribute(
        'aria-expanded',
        'true'
      )
    )
  })

  it('stops saying services failed once a later refresh brought them in', async () => {
    const user = userEvent.setup()
    const { services } = renderTree({ showServices: true })
    vi.mocked(services.apis.mapStates.fetchFolderHostServices).mockRejectedValueOnce(
      new Error('site down')
    )
    await waitForRows()

    const [webChevron] = screen.getAllByRole('button', { name: 'Expand' })
    await user.click(webChevron!)
    await waitFor(() => expect(screen.getByText('Could not load services')).toBeInTheDocument())

    vi.mocked(services.apis.mapStates.fetchFolderHostServices).mockResolvedValue([
      {
        name: 'CPU load',
        state: 'OK',
        output: '',
        acknowledged: false,
        in_downtime: false,
        is_flapping: false
      }
    ])
    services.states.folderTreeVersion.value += 1

    await waitFor(() => expect(screen.getByText('CPU load')).toBeInTheDocument())
    expect(screen.queryByText('Could not load services')).toBeNull()
  })

  it('keeps drawing a folder that matches by name even though it holds no hosts', async () => {
    const tree = aFolderNode({
      path: '/main',
      title: 'Main',
      kind: 'folder',
      host_count: 1,
      children: [
        aFolderNode({ path: '/main/staging', title: 'Staging', kind: 'folder', is_empty: true }),
        aFolderNode({ path: '/main/web-01', title: 'web-01', kind: 'host', state: 'UP' })
      ]
    })
    const { rerender } = renderTree({ tree })
    await waitFor(() => expect(screen.getAllByRole('treeitem')).toHaveLength(3))

    await rerender({ needle: 'staging' })
    // The empty state is held back until the server search has answered, so the
    // assertion has to wait for the answer rather than race it.
    await new Promise((resolve) => setTimeout(resolve, AFTER_THE_DEBOUNCE_MS))

    expect(screen.queryByText('No matches for the current filter.')).toBeNull()
    expect(screen.getByRole('treeitem', { name: /Staging/ })).toBeInTheDocument()
  })

  it('drops a search answer that arrives after the box was cleared', async () => {
    const { services, rerender } = renderTree({ showServices: true })
    // A search the server has not answered yet, held open across the clearing.
    let answer: (result: FolderServiceSearchResult) => void = () => {}
    vi.mocked(services.apis.mapStates.searchFolderServices).mockReturnValue(
      new Promise<FolderServiceSearchResult>((resolve) => {
        answer = resolve
      })
    )
    await waitForRows()

    await rerender({ needle: 's:cpu' })
    await new Promise((resolve) => setTimeout(resolve, AFTER_THE_DEBOUNCE_MS))
    await rerender({ needle: '' })
    await new Promise((resolve) => setTimeout(resolve, AFTER_THE_DEBOUNCE_MS))

    answer({
      matches: [
        {
          host: 'web-01',
          site_id: null,
          services: [
            {
              name: 'CPU load',
              state: 'OK',
              output: '',
              acknowledged: false,
              in_downtime: false,
              is_flapping: false
            }
          ]
        }
      ],
      truncated: true,
      limit: 1
    })
    await new Promise((resolve) => setTimeout(resolve, 50))

    // The emptied box asks nothing of the server, so nothing of that answer
    // may reach the screen.
    expect(screen.queryByText(/more matches exist/)).toBeNull()
    expect(screen.queryByText('CPU load')).toBeNull()
  })

  it('fetches a host services again on the next map instead of reusing the last one', async () => {
    const user = userEvent.setup()
    const { services, rerender } = renderTree({ showServices: true })
    vi.mocked(services.apis.mapStates.fetchFolderHostServices).mockResolvedValue([
      {
        name: 'CPU load',
        state: 'OK',
        output: '',
        acknowledged: false,
        in_downtime: false,
        is_flapping: false
      }
    ])
    await waitForRows()

    const [webChevron] = screen.getAllByRole('button', { name: 'Expand' })
    await user.click(webChevron!)
    await waitFor(() => expect(screen.getByText('CPU load')).toBeInTheDocument())

    // The same host name on another map is another host, with its own services.
    vi.mocked(services.apis.mapStates.fetchFolderHostServices).mockResolvedValue([
      {
        name: 'Disk /',
        state: 'OK',
        output: '',
        acknowledged: false,
        in_downtime: false,
        is_flapping: false
      }
    ])
    await rerender({ config: aFolderTreeMap('map2', true) })

    const [webChevronAgain] = screen.getAllByRole('button', { name: 'Expand' })
    await user.click(webChevronAgain!)
    await waitFor(() => expect(screen.getByText('Disk /')).toBeInTheDocument())
    expect(screen.queryByText('CPU load')).toBeNull()
  })

  it('drops a host services answer that arrives after the map was switched', async () => {
    const user = userEvent.setup()
    const { services, rerender } = renderTree({ showServices: true })
    // The first map's fetch, held open across the switch to the next map, where
    // the host of the same name answers with its own services.
    let answerFirstMap: (services: FolderHostService[]) => void = () => {}
    vi.mocked(services.apis.mapStates.fetchFolderHostServices)
      .mockReturnValueOnce(
        new Promise<FolderHostService[]>((resolve) => {
          answerFirstMap = resolve
        })
      )
      .mockResolvedValue([aService('Disk /')])
    await waitForRows()

    const [webChevron] = screen.getAllByRole('button', { name: 'Expand' })
    await user.click(webChevron!)
    await rerender({ config: aFolderTreeMap('map2', true) })
    const [webChevronAgain] = screen.getAllByRole('button', { name: 'Expand' })
    await user.click(webChevronAgain!)
    await waitFor(() => expect(screen.getByText('Disk /')).toBeInTheDocument())

    answerFirstMap([aService('CPU load')])
    await new Promise((resolve) => setTimeout(resolve, 50))

    // A host of the same name on the next map is a different host. Nothing
    // would put that right later either: the switch dropped the host from the
    // refresh loop along with the rest of the previous map's cache.
    expect(screen.queryByText('CPU load')).toBeNull()
    expect(screen.getByText('Disk /')).toBeInTheDocument()
  })

  it('takes the folder menu of the map being left off the screen', async () => {
    const user = userEvent.setup()
    const { rerender } = renderTree()
    await waitForRows()

    await user.pointer({ keys: '[MouseRight]', target: screen.getAllByRole('treeitem')[0]! })
    await waitFor(() => expect(screen.getByText('Folder')).toBeInTheDocument())

    await rerender({ config: aFolderTreeMap('map2', false) })

    expect(screen.queryByText('Folder')).toBeNull()
  })
})

describe('FolderTreeMapView (map mode)', () => {
  beforeEach(() => {
    // jsdom has no layout, so the stage reports its size the moment it is observed.
    vi.stubGlobal(
      'ResizeObserver',
      class {
        constructor(private readonly onResize: ResizeObserverCallback) {}
        observe(): void {
          this.onResize(
            [{ contentRect: { width: 800, height: 600 } }] as unknown as ResizeObserverEntry[],
            this as unknown as ResizeObserver
          )
        }
        unobserve() {}
        disconnect() {}
      }
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('opens the same hover card as the list on a host tile, with the host own state', async () => {
    // The tile is yellow for a failing service; the card speaks for the host.
    renderTree({
      drawing: 'map',
      tree: aFolderNode({
        path: '/main',
        title: 'Main',
        kind: 'folder',
        host_count: 1,
        children: [
          aFolderNode({
            path: '/main/web-01',
            title: 'web-01',
            kind: 'host',
            state: 'WARNING',
            own_state: 'UP'
          })
        ]
      })
    })

    const tile = await screen.findByRole('button', { name: /web-01/ })
    await fireEvent.mouseMove(tile, { clientX: 100, clientY: 100 })

    expect(await screen.findByText('UP')).toBeInTheDocument()
    expect(screen.getByText('Host')).toBeInTheDocument()
  })

  it('names a host tile by the host own state, with the worse service state beside it', async () => {
    renderTree({
      drawing: 'map',
      tree: aFolderNode({
        path: '/main',
        title: 'Main',
        kind: 'folder',
        host_count: 1,
        children: [
          aFolderNode({
            path: '/main/web-01',
            title: 'web-01',
            kind: 'host',
            state: 'WARNING',
            own_state: 'UP'
          })
        ]
      })
    })

    expect(
      await screen.findByRole('button', { name: 'web-01, Up, worst service Warning' })
    ).toBeInTheDocument()
  })

  it('keeps a host card where it opened while the pointer moves within the tile', async () => {
    // A card that followed the pointer across a large tile could never be reached.
    const { container } = renderTree({ drawing: 'map' })
    const tile = await screen.findByRole('button', { name: /web-01/ })

    await fireEvent.mouseMove(tile, { clientX: 100, clientY: 100 })
    const card = await waitFor(() => {
      const element = container.ownerDocument.querySelector<HTMLElement>('.maps-hover-menu')
      expect(element?.style.left).toBeTruthy()
      return element!
    })
    const opened = { left: card.style.left, top: card.style.top }

    await fireEvent.mouseMove(tile, { clientX: 140, clientY: 130 })

    expect({ left: card.style.left, top: card.style.top }).toEqual(opened)
  })

  it('keeps the host card when the pointer only crosses another tile on its way to it', async () => {
    const { container } = renderTree({ drawing: 'map' })
    const host = await screen.findByRole('button', { name: /web-01/ })
    await fireEvent.mouseMove(host, { clientX: 100, clientY: 100 })
    await screen.findByText('Host')

    const folder = screen.getByRole('button', { name: /^Main/ })
    await fireEvent.mouseLeave(host)
    await fireEvent.mouseMove(folder, { clientX: 105, clientY: 105 })
    await fireEvent.mouseLeave(folder)
    await fireEvent.mouseEnter(container.ownerDocument.querySelector('.maps-hover-card')!)
    await new Promise((resolve) => setTimeout(resolve, HOVER_REST_MS + 100))

    expect(screen.getByText('Host')).toBeInTheDocument()
    expect(screen.queryByText('Folder')).toBeNull()
  })

  it('hands over from a host card to the folder card at once, never showing both', async () => {
    renderTree({ drawing: 'map' })

    await fireEvent.mouseMove(await screen.findByRole('button', { name: /web-01/ }), {
      clientX: 100,
      clientY: 100
    })
    await screen.findByText('Host')

    await fireEvent.mouseMove(screen.getByRole('button', { name: /^Main/ }), {
      clientX: 300,
      clientY: 20
    })

    expect(await screen.findByText('Folder')).toBeInTheDocument()
    expect(screen.queryByText('Host')).toBeNull()
  })
})
