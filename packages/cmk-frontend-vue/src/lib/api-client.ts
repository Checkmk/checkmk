/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cmkFetch } from '@/lib/cmkFetch'

export type ApiResponseBody<T> = T

export interface ApiOptions {
  headers?: [string, string][]
  credentials?: RequestCredentials
}

export class Api {
  public constructor(
    protected baseUrl: string | null = null,
    protected headers: [string, string][] = []
  ) {}

  public async option(url: string, options: ApiOptions = {}): Promise<ApiResponseBody<unknown>> {
    const params = this.prepareOptions(options, {
      method: 'OPTION'
    })

    return this.fetch(url, params)
  }

  public async get(url: string, options: ApiOptions = {}): Promise<ApiResponseBody<unknown>> {
    const params = this.prepareOptions(options, {
      method: 'GET'
    })

    return this.fetch(url, params)
  }

  public async post(
    url: string,
    body: BodyInit | null = null,
    options: ApiOptions = {}
  ): Promise<ApiResponseBody<unknown>> {
    const params = this.prepareOptions(options, {
      method: 'POST',
      body
    })

    return this.fetch(url, params)
  }

  public async put(
    url: string,
    body: BodyInit | null = null,
    options: ApiOptions = {}
  ): Promise<ApiResponseBody<unknown>> {
    const params = this.prepareOptions(options, {
      method: 'PUT',
      body
    })
    return this.fetch(url, params)
  }

  public async delete(url: string, options: ApiOptions = {}): Promise<ApiResponseBody<unknown>> {
    const params = this.prepareOptions(options, {
      method: 'DELETE'
    })

    return this.fetch(url, params)
  }

  private async fetch(url: string, params: RequestInit): Promise<ApiResponseBody<unknown>> {
    if (this.baseUrl) {
      url = this.baseUrl + url
    }

    const res = await cmkFetch(url, params)
    await res.raiseForStatus()

    return (await res.json()).result
  }

  private prepareOptions(options: ApiOptions, defaults: RequestInit = {}): RequestInit {
    const opt = Object.assign(options, defaults)
    if (!opt.headers) {
      opt.headers = []
    }

    opt.headers = this.headers.concat(opt.headers)

    return opt
  }
}
