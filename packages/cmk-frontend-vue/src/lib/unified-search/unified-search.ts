/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { ref, type Ref } from 'vue'
import { type Api } from '../api-client'

export interface LegacySearchResult {
  result_code: number
  result: string
  severity: string
}

export interface SearchProviderResult<T> {
  provider: string
  result: Promise<T>
}

export class UnifiedSearchResult {
  private results: SearchProviderResult<unknown>[] = []

  constructor(public searchId: string) {}

  public registerProviderResult(res: SearchProviderResult<unknown>): void {
    this.results.push(res)
  }

  public get(provider: string): SearchProviderResult<unknown> | null {
    return this.results[this.results.findIndex((s) => s.provider === provider)] || null
  }
}

export abstract class SearchProvider {
  private api: Api | null = null
  public searchActive: Ref<boolean> = ref(false)
  public searchError: Ref<string | null> = ref(null)
  constructor(
    public id: string,
    public title?: string,
    public sort: number = 0,
    public minInputlength: number = 2
  ) {
    if (!this.title) {
      this.title = this.id
    }
  }

  abstract search(input: string): Promise<unknown>

  public injectApi(api: Api): void {
    this.api = api
  }

  protected getApi(): Api {
    if (this.api) {
      return this.api
    }

    throw new Error('api not set')
  }

  public initSearch<T>(input: string, callback: (input: string) => Promise<T | Error>): Promise<T> {
    this.searchActive.value = true
    return new Promise((resolve) => {
      void callback(input)
        .catch((e) => {
          resolve(e)
        })
        .then((result) => {
          resolve(result as T)
        })
        .finally(() => {
          this.searchActive.value = false
        })
    })
  }
}

export class UnifiedSearch {
  private lastSearchInput = Date.now()
  private onSearchCallback: ((result?: UnifiedSearchResult) => Promise<void> | void) | null = null

  constructor(
    private id: string,
    private api: Api,
    private providers: SearchProvider[]
  ) {
    for (const provider of this.providers) {
      provider.injectApi(this.api)
    }
  }

  public get(providerId?: string): SearchProvider | SearchProvider[] | null {
    if (providerId) {
      return this.providers.find((p) => providerId === p.id) || null
    }

    return this.providers
  }

  public search(input: string): UnifiedSearchResult {
    const usr = new UnifiedSearchResult(this.id)
    for (const provider of this.providers) {
      usr.registerProviderResult({
        provider: provider.id,
        result:
          input.length >= provider.minInputlength
            ? provider.initSearch(input, provider.search.bind(provider))
            : new Promise((resolve) => {
                resolve(null)
              })
      })
    }
    return usr
  }

  public onSearch(callback: (result?: UnifiedSearchResult) => Promise<void> | void) {
    this.onSearchCallback = callback
  }

  public onInput(e: Event) {
    this.lastSearchInput = Date.now()
    const input = e.target as HTMLInputElement
    setTimeout(() => {
      const now = Date.now()
      if (now - this.lastSearchInput > 200) {
        if (this.onSearchCallback) {
          this.onSearchCallback(this.search(input.value)) as void
        }
      } else {
        if (this.onSearchCallback) {
          this.onSearchCallback() as void
        }
      }
    }, 250)
  }
}
