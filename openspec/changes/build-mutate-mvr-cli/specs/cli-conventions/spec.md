# Spec Delta

## Purpose

Fixes the command-line surface and its safety behavior so every command takes the same global flags, never overwrites input by accident, and reports warnings consistently.

## ADDED Requirements

### Requirement: Command form
The program SHALL be invoked as `mutate-mvr [global flags] <info|merge|isolate|delete|ingest> [command flags]`, with global flags `-v`, `-q`, `--dry-run`, `--format text|json` and `--strict`.

#### Scenario: Unknown command
- **WHEN** an unrecognized command is given
- **THEN** the tool exits non-zero and prints the list of valid commands

### Requirement: Inputs are never overwritten by default
A writing command SHALL require `-o OUT`, SHALL refuse an OUT equal to any input unless `--in-place` is given, and with `--in-place` SHALL first save a backup beside the file, never inside the archive.

#### Scenario: Output equals input
- **WHEN** `-o` names an input file without `--in-place`
- **THEN** the tool exits non-zero and changes nothing

### Requirement: Dry run
With `--dry-run`, a command SHALL print what it would add, remove and warn about and SHALL write no file.

#### Scenario: Dry-run merge
- **WHEN** `--dry-run merge a.mvr b.mvr -o out.mvr` runs
- **THEN** the planned changes are printed and out.mvr does not exist afterwards

### Requirement: Warnings do not fail the operation
When an operation can be carried out, the tool SHALL carry it out, print each warning to stderr, and exit 0. With `--strict`, the tool SHALL exit non-zero after writing if any warning was printed.

#### Scenario: Warning with default flags
- **WHEN** a merge produces a fixture id collision
- **THEN** the output is written, the warning is printed, and the exit code is 0

#### Scenario: Warning with --strict
- **WHEN** the same merge runs with `--strict`
- **THEN** the output is written and the exit code is non-zero

### Requirement: Verbosity
`-q` SHALL suppress everything except errors and `--strict` failures; `-v` SHALL additionally print each member added, removed or renamed.

#### Scenario: Quiet run
- **WHEN** a command runs with `-q` and produces warnings
- **THEN** no warning is printed but `--strict` still sets the exit code
