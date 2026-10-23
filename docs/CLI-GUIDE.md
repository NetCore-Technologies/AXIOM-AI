# AXIOM CLI guide

AXIOM's CLI supports human-readable terminal output and versioned JSON for the
commands that document `--json`. Use `axiom --help` and each group's
`--help` to inspect the command options installed on your machine.

## Shell completion

The root Typer command exposes shell completion. Install completion in the
current user's shell configuration with:

```bash
axiom --install-completion
```

Preview the generated completion script without changing shell configuration:

```bash
axiom --show-completion bash
axiom --show-completion zsh
axiom --show-completion fish
axiom --show-completion powershell
```

The preview command writes the script to standard output. Redirect it to a
file only when you deliberately want to inspect or manage that generated file.
If the shell was already open, restart it or source the appropriate generated
completion script according to the shell's own conventions.

## Configuration validation and repair guidance

The command `axiom config validate --path axiom.yaml --json` emits a
versioned validation report with a stable `error_code` and safe
`suggestions` when it finds a problem. The suggestions are advisory:
`repair_applied` remains false and the command never rewrites the supplied
file. Symlinks are rejected, file contents are not echoed, and oversized files are
rejected before their contents are read.

## Machine-readable output

Commands that support `--json` emit a versioned payload on standard output.
For example:

```bash
axiom status --json
axiom summary --json
axiom model list --json
axiom dataset inspect ./data/train.jsonl --json
axiom engine discover --json
```

JSON mode does not imply that a requested action succeeded: validation and
operation failures keep a non-zero exit code. Commands without a documented
JSON option retain human-oriented output.

## Local Control Center

Run `axiom gui` to start the API on loopback and open the bundled Control
Center. The default port is `40507`; set `AXIOM_GUI_PORT` to choose a different
default, or pass `--port` explicitly. The explicit command-line option takes
precedence over the environment variable. Port `0` asks the operating system to
select an available port for that launch.

See [API environment configuration](API.md) and [data retention](DATA-RETENTION.md)
for the associated network and local-storage boundaries.
