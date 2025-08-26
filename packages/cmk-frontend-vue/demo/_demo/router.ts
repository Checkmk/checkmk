/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
//
import { pages as componentsPages } from '@demo/components/'
import { pages as formPages } from '@demo/form/'
import { type RouteLocation, createRouter, createWebHistory } from 'vue-router'

import DemoEmpty from './DemoEmpty.vue'
import DemoHome from './DemoHome.vue'
import { Folder, Page, RootFolder } from './page'
import type { RRSVMetaFolder, Route } from './types'

const root: RootFolder = new RootFolder(DemoHome, [
  new Folder('components', DemoEmpty, componentsPages),
  new Folder('form', DemoEmpty, formPages)
])

function defaultProps(route: RouteLocation): { screenshotMode: boolean } {
  return { screenshotMode: route.query.screenshot === 'true' }
}

function toRoute(element: Page | Folder | RootFolder, prefixPath: string): Array<Route> {
  if (element instanceof Page) {
    return [
      {
        path: `${prefixPath}${element.name}`,
        meta: { type: 'page', name: element.name, inFolder: prefixPath },
        props: defaultProps,
        component: element.component
      }
    ]
  } else {
    let folderPath
    let name
    let inFolder
    if (element instanceof Folder) {
      folderPath = `${prefixPath}${element.name}/`
      name = element.name
      inFolder = prefixPath
    } else if (element instanceof RootFolder) {
      folderPath = '/'
      name = '◉'
      inFolder = '////' // does not exist so it's now shown in the nav
    } else {
      throw new Error('not implemented')
    }
    let pages: Array<Route> = []
    const folder: Route<RRSVMetaFolder> = {
      path: folderPath,
      meta: {
        type: 'folder',
        name: name,
        content: pages,
        inFolder: inFolder
      },
      props: defaultProps,
      component: element.component
    }
    for (const subPage of element.pages) {
      pages = [...pages, ...toRoute(subPage, folderPath)]
    }
    pages.sort((a, b) => a.meta.name.localeCompare(b.meta.name))
    folder.meta.content = pages
    return [folder, ...pages]
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: toRoute(root, '/')
})

export default router
