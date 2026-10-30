/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'
import * as vscode from 'vscode'

import { shellEscape } from '../core/config'
import { log, notifyError } from '../core/log'
import { PipxUpdateCheck } from '../core/pipxUpdate'
import { safeExecAsync } from '../core/shell'
import { getExtendedPath } from '../core/tasks'
import { type PlaybookRunPreset, PlaybookRunWizard } from './cmkUpWizard'
import { detectOmdSites } from './omd'
import { ensureKeepaliveAuth, runInteractiveInKeepaliveTerminal } from './sudoBridge'

export type PlaybookSource = 'workspace' | 'directory' | 'shipped'

export interface Playbook {
  name: string
  target: string
  file: string
  source: PlaybookSource
  description: string
}

export interface PlaybookPhase {
  name: string
  sites: string
  description: string
}

export interface PlaybookRunOptions {
  phases: string[]
  keep: boolean
  purge: boolean
  dryRun: boolean
  verify: boolean
}

export class CmkUp {
  static readonly PACKAGE = 'cmk-werk-zeug'
  static readonly NAME = 'cmk-up'
  static readonly UVX_COMMAND = 'uvx --from cmk-werk-zeug@latest cmk-up'
  static readonly EXIT_REASONS: Readonly<Record<number, string>> = {
    1: 'playbook or arguments',
    2: 'site or omd problem on this machine',
    3: 'apply failed',
    4: 'verification failed'
  }
  private static readonly SHEBANG = /^#!.*\bcmk-up\b/
  private static readonly YAML = /\.ya?ml$/
  private static readonly HEADER_BYTES = 4096
  private static readonly WORKSPACE_EXCLUDE =
    '{**/node_modules/**,**/bazel-*/**,**/.venv/**,**/.git/**}'
  private static readonly WORKSPACE_LIMIT = 5000
  private static readonly UVX_PYTHON = 'uvx --from cmk-werk-zeug@latest python'
  private static readonly SHIPPED_LISTING =
    '-c "import cwz, pathlib; ' +
    "print(*sorted(map(str, (pathlib.Path(cwz.__file__).parent / 'example-playbooks').glob('*.yaml'))), sep=chr(10))\""
  private static readonly INTERPRETER = /^#!(\/\S*python[\d.]*)\s*$/
  private static readonly UVX_TIMEOUT = 120_000

  private _playbooks: Playbook[] = []
  private _files = new Set<string>()
  private _own: Playbook[] = []
  private _shipped: Playbook[] = []
  private _shippedLoad: Promise<Playbook[]> | null = null
  private _scan: Promise<void> | null = null
  private _scanned = false
  private _installed: boolean | null = null
  private _executable: Promise<string> | null = null
  private _onRefresh: (() => void) | null = null
  private _onSitesChanged: (() => Promise<void>) | null = null
  private readonly _wizard = new PlaybookRunWizard(this)
  private readonly _updates = new PipxUpdateCheck(CmkUp.PACKAGE, 'cmk.cwz.lastPypiCheck')

  static isPlaybook(header: string): boolean {
    return CmkUp.SHEBANG.test(header.split('\n', 1)[0])
  }

  static describe(header: string): string {
    for (const line of header.split('\n').slice(1)) {
      if (!line.startsWith('#')) break
      const text = line.replace(/^#\s?/, '')
      if (!text.trim() || text.startsWith(' ') || text.startsWith('hint:')) continue
      return text.trim()
    }
    return ''
  }

  static parsePhases(raw: string): PlaybookPhase[] {
    return raw
      .split('\n')
      .filter((line) => line.trim())
      .map((line) => {
        const [name, sites = '', ...description] = line.split('\t')
        return { name, sites, description: description.join('\t') }
      })
  }

  static enrollArgs(file: string, site: string): string[] {
    return ['--enroll', file, '--only-site', site]
  }

  static runArgs(target: string, options: PlaybookRunOptions): string[] {
    const args = [target]
    for (const phase of options.phases) args.push('--phase', phase)
    if (options.keep) args.push('--keep')
    if (options.purge) args.push('--purge')
    if (options.dryRun) args.push('--dry-run')
    if (options.verify) args.push('--verify')
    return args
  }

  static commandLine(args: string[], command: string = CmkUp.UVX_COMMAND): string {
    return [command, ...args.map((arg) => CmkUp.quote(arg))].join(' ')
  }

  static installedCommand(executable: string): string {
    return executable ? CmkUp.quote(executable) : CmkUp.UVX_COMMAND
  }

  static interpreter(header: string): string {
    const python = CmkUp.INTERPRETER.exec(header.split('\n', 1)[0])?.[1]
    return python ? CmkUp.quote(python) : CmkUp.UVX_PYTHON
  }

  private static quote(arg: string): string {
    return /^[\w@%+=:,./-]+$/.test(arg) ? arg : shellEscape(arg)
  }

  register(context: vscode.ExtensionContext, onSitesChanged: () => Promise<void>): void {
    this._onSitesChanged = onSitesChanged
    context.subscriptions.push(
      vscode.commands.registerCommand('cmk.cmkUp.run', (uri?: vscode.Uri) =>
        this.startRun(uri instanceof vscode.Uri ? uri.fsPath : undefined)
      ),
      vscode.commands.registerCommand('cmk.cmkUp.init', () => this.init()),
      vscode.commands.registerCommand('cmk.cmkUp.install', () => this.install()),
      vscode.commands.registerCommand('cmk.cmkUp.enroll', (site?: string) => this.enroll(site)),
      vscode.window.onDidChangeActiveTextEditor((editor) => {
        if (editor) this.noteDocument(editor.document)
      }),
      vscode.workspace.onDidSaveTextDocument((document) => this.noteDocument(document)),
      vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration('cmk.cmkUp')) void this.rescan()
      })
    )
    void this.rescan().then(() => {
      const editor = vscode.window.activeTextEditor
      if (editor) this.noteDocument(editor.document)
    })
    void this._updates.run(context)
  }

  setRefreshCallback(cb: () => void): void {
    this._onRefresh = cb
  }

  snapshot(): Playbook[] {
    if (!this._scanned) void this.rescan()
    void this.loadShipped()
    return this._playbooks
  }

  scanned(): boolean {
    return this._scanned
  }

  installed(): boolean | null {
    return this._installed
  }

  async install(): Promise<void> {
    await this._updates.install()
    await this.rescan()
  }

  async playbooks(): Promise<Playbook[]> {
    if (!this._scanned) await this.rescan()
    await this.loadShipped()
    return this._playbooks
  }

  rescan(): Promise<void> {
    this._scan ??= this.scan().finally(() => {
      this._scan = null
    })
    return this._scan
  }

  async listPhases(target: string): Promise<PlaybookPhase[]> {
    return CmkUp.parsePhases(await this.exec([target, '--list-phases']))
  }

  startRun(target?: string, preset?: PlaybookRunPreset): Promise<void> {
    return this._wizard.start(target, preset)
  }

  async init(): Promise<void> {
    const uri = await vscode.window.showSaveDialog({
      title: 'New cmk-up playbook',
      defaultUri: vscode.Uri.file(path.join(this.newPlaybookDirectory(), 'scenario.yaml')),
      filters: { 'cmk-up playbook': ['yaml', 'yml'] }
    })
    if (!uri) return
    fs.rmSync(uri.fsPath, { force: true })
    log(`cmk-up: --init ${uri.fsPath}`)
    await this.exec(['--init', uri.fsPath])
    if (!fs.existsSync(uri.fsPath)) {
      void notifyError(`cmk-up --init did not write ${uri.fsPath}`)
      return
    }
    await this.openAndRescan(uri.fsPath)
  }

  async openAndRescan(file: string): Promise<void> {
    await vscode.window.showTextDocument(vscode.Uri.file(file))
    await this.rescan()
  }

  async revealDirectory(dir: string): Promise<void> {
    if (!this.createDirectory(dir)) {
      void notifyError(`cmk-up: cannot create ${dir}`)
      return
    }
    await vscode.commands.executeCommand('revealFileInOS', vscode.Uri.file(dir))
  }

  private newPlaybookDirectory(): string {
    const local = this.directories()[0]
    if (local && this.createDirectory(local)) return local
    return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? os.homedir()
  }

  private createDirectory(dir: string): boolean {
    try {
      fs.mkdirSync(dir, { recursive: true })
      return true
    } catch (e) {
      log(`cmk-up: cannot create ${dir}: ${e}`)
      return false
    }
  }

  async enroll(site?: string): Promise<void> {
    site ??= (
      await vscode.window.showQuickPick(
        detectOmdSites().map((s) => ({ label: s.name, description: s.version })),
        { title: 'cmk-up: create playbook from site' }
      )
    )?.label
    if (!site) return
    const uri = await vscode.window.showSaveDialog({
      title: `Playbook that rebuilds ${site}`,
      defaultUri: vscode.Uri.file(path.join(this.newPlaybookDirectory(), `${site}.yaml`)),
      filters: { 'cmk-up playbook': ['yaml', 'yml'] }
    })
    if (!uri) return
    fs.rmSync(uri.fsPath, { force: true })
    const exitCode = await this.runInKeepalive(CmkUp.enrollArgs(uri.fsPath, site))
    if (exitCode === 0 && fs.existsSync(uri.fsPath)) await this.openAndRescan(uri.fsPath)
  }

  async run(target: string, options: PlaybookRunOptions): Promise<number | null> {
    return this.runInKeepalive(CmkUp.runArgs(target, options))
  }

  private async runInKeepalive(args: string[]): Promise<number | null> {
    if (!(await ensureKeepaliveAuth())) return null
    const command = CmkUp.commandLine(args, await this.command())
    log(`cmk-up: ${command}`)
    const exitCode = await runInteractiveInKeepaliveTerminal(command)
    await this._onSitesChanged?.()
    if (exitCode !== null && exitCode !== 0 && exitCode !== 130) {
      void notifyError(
        `cmk-up failed (exit ${exitCode}: ${CmkUp.EXIT_REASONS[exitCode] ?? 'unknown'})`,
        'See the "OMD: sudo keepalive" terminal for details.'
      )
    }
    return exitCode
  }

  private async exec(args: string[]): Promise<string> {
    const command = CmkUp.commandLine(args, await this.command())
    return safeExecAsync(`PATH=${shellEscape(getExtendedPath())} ${command}`, {
      timeout: CmkUp.UVX_TIMEOUT
    })
  }

  private executable(): Promise<string> {
    this._executable ??= safeExecAsync(
      `PATH=${shellEscape(getExtendedPath())} command -v ${CmkUp.NAME}`
    )
    return this._executable
  }

  private async command(): Promise<string> {
    return CmkUp.installedCommand(await this.executable())
  }

  private async scan(): Promise<void> {
    this._executable = null
    const [workspace, installed] = await Promise.all([
      this.scanWorkspace(),
      this._updates.available()
    ])
    this._installed = installed
    const seen = new Set<string>()
    this._own = [...workspace, ...this.scanDirectories()].filter(
      (p) => !seen.has(p.file) && seen.add(p.file)
    )
    this._files = new Set(this._own.map((p) => p.file))
    this._scanned = true
    this.publishFiles()
    this.publishPlaybooks()
  }

  private loadShipped(): Promise<Playbook[]> {
    this._shippedLoad ??= this.scanShipped().then((shipped) => {
      if (!shipped.length) this._shippedLoad = null
      this._shipped = shipped
      this.publishPlaybooks()
      return shipped
    })
    return this._shippedLoad
  }

  private publishPlaybooks(): void {
    this._playbooks = [...this._own, ...this._shipped]
    this._onRefresh?.()
  }

  private async scanWorkspace(): Promise<Playbook[]> {
    const uris = await vscode.workspace.findFiles(
      '**/*.{yaml,yml}',
      CmkUp.WORKSPACE_EXCLUDE,
      CmkUp.WORKSPACE_LIMIT
    )
    return this.fromFiles(
      uris.map((uri) => uri.fsPath),
      'workspace'
    )
  }

  private scanDirectories(): Playbook[] {
    const files = this.directories().flatMap((dir) => {
      try {
        return fs
          .readdirSync(dir)
          .filter((name) => CmkUp.YAML.test(name))
          .map((name) => path.join(dir, name))
      } catch {
        return []
      }
    })
    return this.fromFiles(files, 'directory')
  }

  directories(): string[] {
    return vscode.workspace
      .getConfiguration('cmk.cmkUp')
      .get<string[]>('playbookDirectories', [])
      .map((dir) => path.resolve(dir.replace(/^~(?=$|\/)/, os.homedir())))
  }

  private async scanShipped(): Promise<Playbook[]> {
    const python = CmkUp.interpreter(this.readHeader(await this.executable()))
    const listing = await safeExecAsync(
      `PATH=${shellEscape(getExtendedPath())} ${python} ${CmkUp.SHIPPED_LISTING}`,
      { timeout: CmkUp.UVX_TIMEOUT }
    )
    return this.fromFiles(listing.split('\n').filter(Boolean), 'shipped')
  }

  private fromFiles(files: string[], source: PlaybookSource): Playbook[] {
    return files.flatMap((file) => {
      const header = this.readHeader(file)
      if (source !== 'shipped' && !CmkUp.isPlaybook(header)) return []
      const name = path.basename(file).replace(CmkUp.YAML, '')
      return [
        {
          name,
          file,
          source,
          target: source === 'shipped' ? name : file,
          description: CmkUp.describe(header)
        }
      ]
    })
  }

  private readHeader(file: string): string {
    let fd: number | undefined
    try {
      fd = fs.openSync(file, 'r')
      const buffer = Buffer.alloc(CmkUp.HEADER_BYTES)
      const read = fs.readSync(fd, buffer, 0, CmkUp.HEADER_BYTES, 0)
      return buffer.toString('utf-8', 0, read)
    } catch {
      return ''
    } finally {
      if (fd !== undefined) fs.closeSync(fd)
    }
  }

  private noteDocument(document: vscode.TextDocument): void {
    if (document.uri.scheme !== 'file' || !CmkUp.YAML.test(document.fileName)) return
    const isPlaybook = CmkUp.isPlaybook(document.lineAt(0).text)
    if (isPlaybook === this._files.has(document.fileName)) return
    if (isPlaybook) this._files.add(document.fileName)
    else this._files.delete(document.fileName)
    this.publishFiles()
    void this.rescan()
  }

  private publishFiles(): void {
    void vscode.commands.executeCommand('setContext', 'cmk.cmkUp.playbookFiles', [...this._files])
  }
}

export const cmkUp = new CmkUp()
