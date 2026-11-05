---
status: 'Superseded: by 0002-python-prototypes.md'
date: 2026-11-05
---

# Discovery before production tooling

## Context and Problem Statement

The camera's supported companion applications are obsolete, and its USB and
Wi-Fi interfaces were undocumented. A replacement needs reliable clock and
recording control without assuming that commands, configuration files or device
clocks behave like those of other action cameras. Camera writes and mode changes
can have effects that outlast an individual request.

## Decision Outcome

Start with research and hardware verification before presenting controls as
working features. The initial implementation direction was a Linux Rust CLI
with separate protocol and presentation crates; [ADR 0002](0002-python-prototypes.md)
supersedes that technology choice with Python prototypes.

Keep transport and protocol logic separate from the user interface. Bound
network waits, preserve unrelated settings, provide clock dry runs and report
whether the camera's resulting state was verified. Do not expose a generic
remote shell as normal application functionality.

## Alternatives Considered

Implementing a full GUI or cross-platform application immediately would depend
on unverified assumptions about camera behavior. Treating a command
acknowledgement as proof of the resulting state would also obscure failures.

## Consequences

Hardware findings and protocol specifications guide implementation, and
unsupported behavior stays explicitly experimental. Proprietary applications,
raw dumps and personal media remain outside the public repository; independently
written documentation and sanitized fixtures can be published.
