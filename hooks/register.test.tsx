import type { On, SessionStartInput } from 'claude-code'
import { describe, expect, test } from 'claude-code/testing'

// The checker is stubbed: these tests pin what the mod does with the JSON
// that `asciid.py check --format json` prints, not the checker itself.

const SESSION: SessionStartInput = { surface: 'terminal', isInteractive: true, cwd: '/work' }

const BOX = '+------+\n| box  |\n+------+\n'
const GLYPHS = '┌──┐\n│  │\n└──┘\n'

const finding = (line: number, col: number, rule: string, severity = 'error') => ({
  line,
  col,
  severity,
  rule,
  message: `${rule} problem`,
  suggestion: null,
})

const report = (path: string, findings: ReturnType<typeof finding>[]) =>
  JSON.stringify({
    version: 1,
    files: [{ path, findings }],
    counts: {
      error: findings.filter(f => f.severity === 'error').length,
      warning: findings.filter(f => f.severity === 'warning').length,
      info: findings.filter(f => f.severity === 'info').length,
    },
  })

type World = {
  argvs: string[][]
  toasts: string[]
  commands: string[]
  reads: string[]
}

type Setup = {
  files: Record<string, string>
  /** What the checker prints for a check of a file (stdout, exit code), or 'throw' when the run fails. */
  check?: (argv: readonly string[]) => { stdout: string; exitCode: number } | 'throw'
  shPython?: { stdout: string; exitCode: number }
  xcodeExit?: number
  /** The tool refuses the call, as the engine would. */
  toolDeny?: string
}

const ok = (stdout: string, exitCode = 0) => ({
  exitCode,
  stdout,
  stderr: '',
  isStdoutTruncated: false,
  isStderrTruncated: false,
})

function worldOf(on: On, setup: Setup): World {
  const world: World = { argvs: [], toasts: [], commands: [], reads: [] }

  on('fs.read', (_, e) => {
    world.reads.push(e.path)

    const text = setup.files[e.path]

    return text === undefined ? { deny: `ENOENT: ${e.path}` } : { value: text }
  })

  on('process.run', (_, e) => {
    world.argvs.push([...e.argv])

    if (e.argv[0] === '/bin/sh') {
      const sh = setup.shPython ?? { stdout: '/opt/homebrew/bin/python3\n', exitCode: 0 }

      return { value: ok(sh.stdout, sh.exitCode) }
    }

    if (e.argv[0] === 'xcode-select') return { value: ok('/Library/Developer/CommandLineTools\n', setup.xcodeExit ?? 0) }

    const out = setup.check?.(e.argv) ?? { stdout: '', exitCode: 0 }

    if (out === 'throw') return { deny: 'the checker could not start' }

    return { value: ok(out.stdout, out.exitCode) }
  })

  on('command.register', (_, e) => {
    world.commands.push(e.name)

    return { value: { command: e.name } }
  })
  on('ui.toast', (_, e) => {
    world.toasts.push(e.text)

    return { value: undefined }
  })
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('tool.call', () => (setup.toolDeny === undefined ? { result: {} } : { deny: setup.toolDeny }))

  return world
}

const checkRuns = (world: World) => world.argvs.filter(a => a.includes('check'))

const write = ($: { tool: { call: (i: never) => Promise<{ context?: readonly string[] }> } }, path: string) =>
  $.tool.call({ tool: 'Write', file_path: path, content: 'x' } as never)

const edit = ($: { tool: { call: (i: never) => Promise<{ context?: readonly string[] }> } }, path: string) =>
  $.tool.call({ tool: 'Edit', file_path: path, old_string: 'a', new_string: 'b' } as never)

const command = (args: string) => ({
  command: 'ascii',
  args,
  origin: { kind: 'composer' as const },
  presentation: { isFullscreen: true, columns: 120 },
})

describe('the check after a write', () => {
  test('a Write of a markdown file with a broken box gets the findings as context, and is not denied', async ($, on) => {
    const bad = report('/work/a.md', [finding(2, 9, 'box'), finding(3, 1, 'connect')])
    const world = worldOf(on, { files: { '/work/a.md': BOX }, check: () => ({ stdout: bad, exitCode: 1 }) })

    await $.session.start(SESSION)

    const ran = await write($, '/work/a.md')

    expect(ran.context?.length).toBe(1)
    expect(ran.context?.[0]).toContain('2 findings in /work/a.md')
    expect(ran.context?.[0]).toContain('/work/a.md:2:9 [box] box problem')
    expect(ran.context?.[0]).toContain('/work/a.md:3:1 [connect] connect problem')
    expect(ran).not.toHaveProperty('deny')

    const run = checkRuns(world)[0]

    expect(run?.slice(-4)).toEqual(['check', '--format', 'json', '/work/a.md'])
    expect(run?.[1]).toMatch(/\/skills\/ascii-diagrams\/scripts\/asciid\.py$/)
  })

  test('a file with side-by-side ASCII boxes on one row is passed to the checker', async ($, on) => {
    const sideBySide = '+-------+     +-------+\n| Alpha  |---->| Beta  |\n+-------+     +-------+\n'
    const bad = report('/work/side.md', [finding(3, 9, 'box')])
    const world = worldOf(on, {
      files: { '/work/side.md': sideBySide },
      check: () => ({ stdout: bad, exitCode: 1 }),
    })

    await $.session.start(SESSION)

    const ran = await write($, '/work/side.md')

    expect(ran.context?.length).toBe(1)
    expect(ran.context?.[0]).toContain('/work/side.md:3:9 [box] box problem')
    expect(checkRuns(world).length).toBe(1)
  })

  test('an Edit is checked the same way, and a file with box-drawing glyphs counts', async ($, on) => {
    const bad = report('/work/notes.txt', [finding(1, 4, 'kink')])
    worldOf(on, { files: { '/work/notes.txt': GLYPHS }, check: () => ({ stdout: bad, exitCode: 1 }) })

    await $.session.start(SESSION)

    expect((await edit($, '/work/notes.txt')).context?.[0]).toContain('1 findings in /work/notes.txt')
  })

  test('only the first ten findings are listed, and the note says how many there are', async ($, on) => {
    const many = Array.from({ length: 14 }, (_, i) => finding(i + 1, 1, 'seam'))
    worldOf(on, {
      files: { '/work/a.md': BOX },
      check: () => ({ stdout: report('/work/a.md', many), exitCode: 1 }),
    })

    await $.session.start(SESSION)

    const note = (await write($, '/work/a.md')).context?.[0] ?? ''

    expect(note).toContain('14 findings')
    expect(note).toContain('first 10 of 14')
    expect(note).toContain('a.md:10:1')
    expect(note).not.toContain('a.md:11:1')
  })

  test('info findings alone leave no note; a warning does', async ($, on) => {
    let output = report('/work/a.md', [finding(1, 1, 'mixed-set', 'info')])
    worldOf(on, { files: { '/work/a.md': BOX }, check: () => ({ stdout: output, exitCode: 0 }) })

    await $.session.start(SESSION)

    expect((await write($, '/work/a.md')).context).toBeUndefined()

    output = report('/work/a.md', [finding(1, 90, 'width', 'warning')])

    expect((await write($, '/work/a.md')).context?.[0]).toContain('1 findings')
  })

  test('a file that is not a listed extension is not read or checked', async ($, on) => {
    const world = worldOf(on, { files: { '/work/a.ts': BOX }, check: () => ({ stdout: '', exitCode: 1 }) })

    await $.session.start(SESSION)

    expect((await write($, '/work/a.ts')).context).toBeUndefined()
    expect(world.reads).toEqual([])
    expect(checkRuns(world)).toEqual([])
  })

  test('a clean markdown file, and one with no diagram in it, run no check or a silent one', async ($, on) => {
    const world = worldOf(on, {
      files: { '/work/clean.md': BOX, '/work/prose.md': 'just words\n| a | b |\n' },
      check: () => ({ stdout: report('/work/clean.md', []), exitCode: 0 }),
    })

    await $.session.start(SESSION)

    expect((await write($, '/work/clean.md')).context).toBeUndefined()
    expect((await write($, '/work/prose.md')).context).toBeUndefined()
    expect(checkRuns(world).length, 'only the file with a diagram is checked').toBe(1)
  })

  test('a failed process, bad JSON or an unreadable file leave the result as it was', async ($, on) => {
    let mode: 'throw' | 'junk' | 'usage' = 'throw'
    worldOf(on, {
      files: { '/work/a.md': BOX },
      check: () => (mode === 'throw' ? 'throw' : { stdout: mode === 'junk' ? 'not json' : '', exitCode: 2 }),
    })

    await $.session.start(SESSION)

    expect((await write($, '/work/a.md')).context).toBeUndefined()
    mode = 'junk'
    expect((await write($, '/work/a.md')).context).toBeUndefined()
    mode = 'usage'
    expect((await write($, '/work/a.md')).context).toBeUndefined()
    expect((await write($, '/work/missing.md')).context).toBeUndefined()
  })

  test('a call the tool refused is passed on untouched, with no check run', async ($, on) => {
    const world = worldOf(on, {
      files: { '/work/a.md': BOX },
      toolDeny: 'not allowed',
      check: () => ({ stdout: '', exitCode: 1 }),
    })

    await $.session.start(SESSION)

    const ran = (await write($, '/work/a.md')) as { deny?: string; context?: readonly string[] }

    expect(ran.deny).toBe('not allowed')
    expect(checkRuns(world)).toEqual([])
  })
})

describe('finding python', () => {
  test('no python3 gives one toast at the start and turns the check off', async ($, on) => {
    const world = worldOf(on, {
      files: { '/work/a.md': BOX },
      shPython: { stdout: '', exitCode: 1 },
      check: () => ({ stdout: report('/work/a.md', [finding(1, 1, 'box')]), exitCode: 1 }),
    })

    await $.session.start(SESSION)

    expect(world.toasts.length).toBe(1)
    expect(world.toasts[0]).toContain('python3 was not found')

    expect((await write($, '/work/a.md')).context).toBeUndefined()
    expect((await write($, '/work/a.md')).context).toBeUndefined()
    expect(world.toasts.length, 'said once').toBe(1)
    expect(checkRuns(world)).toEqual([])
  })

  test('the macOS stub is used only once the Command Line Tools exist', async ($, on) => {
    const world = worldOf(on, {
      files: {},
      shPython: { stdout: '/usr/bin/python3\n', exitCode: 0 },
      xcodeExit: 2,
    })

    await $.session.start(SESSION)

    expect(world.argvs.some(a => a[0] === 'xcode-select')).toBe(true)
    expect(world.toasts.length).toBe(1)
  })

  test('the stub is accepted when xcode-select reports the tools', async ($, on) => {
    const world = worldOf(on, {
      files: { '/work/a.md': BOX },
      shPython: { stdout: '/usr/bin/python3\n', exitCode: 0 },
      check: () => ({ stdout: report('/work/a.md', [finding(1, 1, 'box')]), exitCode: 1 }),
    })

    await $.session.start(SESSION)

    expect((await write($, '/work/a.md')).context?.length).toBe(1)
    expect(checkRuns(world)[0]?.[0]).toBe('/usr/bin/python3')
    expect(world.toasts).toEqual([])
  })
})

describe('the /ascii command', () => {
  test('the start registers it', async ($, on) => {
    const world = worldOf(on, { files: {} })

    await $.session.start(SESSION)

    expect(world.commands).toEqual(['ascii'])
  })

  test('/ascii alone answers a usage with the generator shapes', async ($, on) => {
    worldOf(on, { files: {} })
    await $.session.start(SESSION)

    const { text } = await $.command.run(command(''))

    expect(text).toContain('/ascii check <path>')
    for (const shape of ['table', 'flow', 'tree', 'bar', 'arch', 'seq']) expect(text).toContain(shape)
  })

  test('/ascii check answers the text report, and the JSON summary as context', async ($, on) => {
    const bad = report('/work/a.md', [finding(2, 9, 'box')])
    const world = worldOf(on, {
      files: {},
      check: argv =>
        argv.includes('json')
          ? { stdout: bad, exitCode: 1 }
          : { stdout: '/work/a.md:2:9: error: [box] box problem\n', exitCode: 1 },
    })

    await $.session.start(SESSION)

    const { text, context } = await $.command.run(command('check /work/a.md'))

    expect(text).toBe('/work/a.md:2:9: error: [box] box problem')
    expect(context?.[0]).toContain('1 errors, 0 warnings, 0 info')
    expect(context?.[0]).toContain('/work/a.md:2:9 [box] box problem')
    expect(checkRuns(world).length).toBe(2)
  })

  test('/ascii check of a clean path says so; a usage error is relayed', async ($, on) => {
    let code = 0
    worldOf(on, {
      files: {},
      check: argv =>
        code === 2
          ? { stdout: '', exitCode: 2 }
          : { stdout: argv.includes('json') ? report('/work', []) : '', exitCode: 0 },
    })

    await $.session.start(SESSION)

    expect((await $.command.run(command('check /work'))).text).toBe('No findings in /work.')

    code = 2

    expect((await $.command.run(command('check /work'))).text).toBe('The check could not run.')
  })

  test('/ascii check with the checker unable to start answers text and does not throw', async ($, on) => {
    worldOf(on, { files: {}, check: () => 'throw' })
    await $.session.start(SESSION)

    expect((await $.command.run(command('check /work/a.md'))).text).toContain('could not run')
  })
})

describe('the trigger card', () => {
  const compose = {
    model: 'm',
    promptModel: 'm',
    surfaces: [],
    tools: [],
    outputStyle: null,
    traits: [],
  } as never

  test('is one extra section naming the skill, after those beneath', async ($, on) => {
    worldOf(on, { files: {} })
    on('prompt.compose', () => ({ sections: [{ id: 'intro', text: 'hello', scope: 'shared' as const }] }))

    const { sections } = await $.prompt.compose(compose)

    expect(sections.map(s => s.id)).toEqual(['intro', 'ascii-diagrams:trigger'])
    expect(sections[1]?.text).toContain('ascii-diagrams skill')
    expect((sections[1]?.text.split(/\s+/).length ?? 0) < 70).toBe(true)
  })
})

describe('the options', () => {
  test('the python option is used for the check and the search for python3 is skipped', { options: { python: '/custom/python3' } }, async ($, on) => {
    const world = worldOf(on, {
      files: { '/work/a.md': BOX },
      check: () => ({ stdout: report('/work/a.md', [finding(1, 1, 'box')]), exitCode: 1 }),
    })

    await $.session.start(SESSION)

    expect((await write($, '/work/a.md')).context?.length).toBe(1)
    expect(checkRuns(world)[0]?.[0]).toBe('/custom/python3')
    expect(world.argvs.some(a => a[0] === '/bin/sh')).toBe(false)
  })

  test('the extensions option replaces the default list', { options: { extensions: '.rst' } }, async ($, on) => {
    const world = worldOf(on, {
      files: { '/work/a.md': BOX, '/work/a.rst': BOX },
      check: () => ({ stdout: report('/work/a.rst', [finding(1, 1, 'box')]), exitCode: 1 }),
    })

    await $.session.start(SESSION)

    expect((await write($, '/work/a.md')).context).toBeUndefined()
    expect((await write($, '/work/a.rst')).context?.length).toBe(1)
    expect(checkRuns(world).length).toBe(1)
  })

  test('triggerCard false leaves the card out', { options: { triggerCard: false } }, async ($, on) => {
    worldOf(on, { files: {} })
    on('prompt.compose', () => ({ sections: [{ id: 'intro', text: 'hello', scope: 'shared' as const }] }))

    const { sections } = await $.prompt.compose({
      model: 'm',
      promptModel: 'm',
      surfaces: [],
      tools: [],
      outputStyle: null,
      traits: [],
    } as never)

    expect(sections.map(s => s.id)).toEqual(['intro'])
  })
})
