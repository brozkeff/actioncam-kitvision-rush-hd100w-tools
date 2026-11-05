---
status: Accepted
date: 2026-11-05
---

# Python prototypes before Rust

## Context and Problem Statement

The project needs to investigate an old camera protocol and deliver useful
Linux tooling while behavior remains uncertain. Network requests, binary frame
parsing and process supervision benefit from quick iteration and do not yet
show a need for a native implementation. The requested initial environment is
Python 3.15 managed with uv.

## Decision Outcome

Use Python 3.15 with a project-local environment and uv lockfile for the first
implementation. Prefer the standard library for protocol and network I/O, and
use Ruff and ty for development checks. Separate protocol operations from CLI
presentation and record verified behavior in the technical documentation.

Continue with Python until a concrete deployment, performance or platform
integration requirement justifies evaluating another implementation. This
supersedes the initial Rust technology choice in
[ADR 0001](0001-discovery-first.md); its discovery and verification principles
remain in effect. [ADR 0003](0003-linux-webcam.md) covers video integration.

## Alternatives Considered

- **Rust first:** could support a compact native application, but would add
  implementation effort before protocol and product requirements are settled.
- **Python plus existing native tools:** supports rapid experimentation while
  delegating video processing to established software.

## Consequences

The current tooling needs a compatible Python environment and uv setup. There
are no third-party Python runtime dependencies; FFmpeg and Linux webcam tools
are separate system requirements for virtual-camera use. A future Rust or
other-platform implementation can follow the documented protocol without
requiring a rewrite now. Recording and clock persistence still need hardware
validation; language choice does not resolve those device uncertainties.
