import type { EngineInterface, Register } from 'claude-code'

// The mod: after a Write or Edit of a text file that holds a box diagram, run
// the checker and hand its findings to the model. It warns and never denies,
// so a lint cannot block writing.

type Finding = {
  line: number
  col: number
  severity: string
  rule: string
  message: string
  suggestion?: string | null
}

type Report = {
  files: { path: string; findings: Finding[] }[]
  counts: { error: number; warning: number; info: number }
}

const SCRIPT = 'skills/ascii-diagrams/scripts/asciid.py'
const DEFAULT_EXTENSIONS = '.md,.markdown,.txt'
const LISTED = 10
const TIMEOUT_MS = 10000

const GLYPH = /[─-╿]/
const BORDER_ROW = /^[^\n]*\+[-=]{2,}\+/m

const USAGE = [
  '/ascii check <path>   check the box diagrams in a file or folder',
  'Generators (run with the skill): table, flow, tree, bar, arch, seq.',
  'Example: python3 <skill folder>/scripts/asciid.py gen table --style light < payload.json',
].join('\n')

const TRIGGER_CARD =
  'Before typing a box diagram, table or flow in chat, a document or a code comment, use the ' +
  'ascii-diagrams skill: generate it with its generators where a shape fits, otherwise draw it ' +
  'and run its check until it reports no errors.'

type Engine = EngineInterface

const parseReport = (stdout: string): Report | undefined => {
  try {
    const data: unknown = JSON.parse(stdout)
    const r = data as Partial<Report> | null

    if (r === null || typeof r !== 'object' || !Array.isArray(r.files)) return undefined
    if (r.counts === undefined || typeof r.counts.error !== 'number' || typeof r.counts.warning !== 'number') {
      return undefined
    }

    return r as Report
  } catch {
    return undefined
  }
}

// The errors and warnings, as `path:line:col [rule] message`, the first LISTED of them.
const describe = (report: Report): { count: number; lines: string[] } => {
  const all = report.files.flatMap(file =>
    (file.findings ?? [])
      .filter(f => f.severity === 'error' || f.severity === 'warning')
      .map(f => `${file.path}:${f.line}:${f.col} [${f.rule}] ${f.message}`),
  )
  const count = report.counts.error + report.counts.warning

  return { count, lines: all.slice(0, LISTED) }
}

// What the options say, and the interpreter found once per session
// (its path, or null when there is none).
type Config = {
  extensions: string[]
  python: string
  pythonPromise: Promise<string | null> | undefined
}

async function findPython($: Engine, cfg: Config): Promise<string | null> {
  if (cfg.python !== '') return cfg.python

  const found = await $.process.run(['/bin/sh', '-c', 'command -v python3'])
  const path = found.stdout.trim()

  if (found.exitCode !== 0 || path === '') return null

  // On macOS the stub at /usr/bin/python3 opens the Command Line Tools
  // install dialog when the tools are missing: ask first.
  if (path === '/usr/bin/python3') {
    const tools = await $.process.run(['xcode-select', '-p']).catch(() => undefined)

    if (tools !== undefined && tools.exitCode !== 0) return null
  }

  return path
}

function pythonOf($: Engine, cfg: Config): Promise<string | null> {
  cfg.pythonPromise ??= findPython($, cfg)
    .catch(() => null)
    .then(path => {
      if (path === null) {
        $.ui.toast(
          `${$.plugin.name}: python3 was not found. Install Python 3.9 or newer ` +
            '(on a Mac: xcode-select --install) or set the python option. Diagram checks are off this session.',
        )
      }

      return path
    })

  return cfg.pythonPromise
}

type Ran = { deny?: string; isError?: true; context?: readonly string[] }

async function lint<R extends Ran>($: Engine, cfg: Config, ran: R, path: string): Promise<R> {
  try {
    if (ran.deny !== undefined || ran.isError === true) return ran

    const lower = path.toLowerCase()

    if (!cfg.extensions.some(x => lower.endsWith(x))) return ran

    const text = await $.fs.read(path)

    if (typeof text !== 'string' || !(GLYPH.test(text) || BORDER_ROW.test(text))) return ran

    const python = await pythonOf($, cfg)

    if (python === null) return ran

    const out = await $.process.run(
      [python, `${$.plugin.root}/${SCRIPT}`, 'check', '--format', 'json', path],
      { timeoutMs: TIMEOUT_MS },
    )
    const report = parseReport(out.stdout)

    if (report === undefined) return ran

    const { count, lines } = describe(report)

    if (count === 0) return ran

    const more = count > lines.length ? ` (first ${lines.length} of ${count})` : ''
    const note = `${$.plugin.name}: ${count} findings in ${path}${more}: ${lines.join('; ')}`

    return { ...ran, context: [...(ran.context ?? []), note] }
  } catch {
    return ran
  }
}

async function runCheck($: Engine, cfg: Config, args: string): Promise<{ text: string; context?: string[] }> {
  const match = /^check\s+(.+)$/.exec(args.trim())

  if (match === null || match[1] === undefined) return { text: USAGE }

  const path = match[1].trim().replace(/^(["'])(.*)\1$/, '$2')

  try {
    const python = await pythonOf($, cfg)

    if (python === null) return { text: `${$.plugin.name}: python3 was not found; set the python option.` }

    const script = `${$.plugin.root}/${SCRIPT}`
    const shown = await $.process.run([python, script, 'check', path], { timeoutMs: TIMEOUT_MS })

    if (shown.exitCode > 1) return { text: 'The check could not run.' }

    const json = await $.process.run([python, script, 'check', '--format', 'json', path], {
      timeoutMs: TIMEOUT_MS,
    })
    const report = parseReport(json.stdout)
    const text = shown.stdout.trim() === '' ? `No findings in ${path}.` : shown.stdout.trim()

    if (report === undefined) return { text }

    const { count, lines } = describe(report)
    const c = report.counts
    const summary = `${$.plugin.name} check ${path}: ${c.error} errors, ${c.warning} warnings, ${c.info} info.`

    return { text, context: [count > 0 ? `${summary} ${lines.join('; ')}` : summary] }
  } catch {
    return { text: `${$.plugin.name}: the check could not run.` }
  }
}

export const register: Register = (on, options) => {
  const cfg: Config = {
    extensions: String(options.extensions ?? DEFAULT_EXTENSIONS)
      .split(',')
      .map(x => x.trim().toLowerCase())
      .filter(x => x !== ''),
    python: typeof options.python === 'string' ? options.python.trim() : '',
    pythonPromise: undefined,
  }
  const isCardOn = options.triggerCard !== false

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'ascii',
      description: 'Check the box diagrams in a file or folder.',
      argumentHint: 'check <path>',
    })
    // Resolve the interpreter now, so a missing one is said once, early.
    await pythonOf($, cfg)

    return next(e)
  })

  on('tool.call', { tool: 'Write' }, async ($, e, next) => lint($, cfg, await next(e), e.file_path)).catch(
    ($, e, next) => next(e),
  )

  on('tool.call', { tool: 'Edit' }, async ($, e, next) => lint($, cfg, await next(e), e.file_path)).catch(
    ($, e, next) => next(e),
  )

  on('command.run', { command: 'ascii' }, ($, e) => runCheck($, cfg, e.args))

  if (isCardOn) {
    on('prompt.compose', async ($, e, next) => {
      const composed = await next(e)

      return {
        sections: [...composed.sections, { id: `${$.plugin.name}:trigger`, text: TRIGGER_CARD, scope: 'session' as const }],
      }
    })
  }
}
