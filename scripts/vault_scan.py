"""Canonical vault-scanning policy: which directories every tool skips.

Six tools each carried their own hardcoded exclude set. Only five entries were
common to all six, and the differences were a mix of two very different things:

  Real intent, worth keeping
    export_okf skips `excalidraw`  - drawings are not exportable prose
    vault_stats skips `raw`/`references` - not user notes for counting purposes

  Drift, which is the bug
    `_trash` appeared in 4 of 6, `node_modules` in 4 of 6
    agent config dirs (.agents, .codex, .gemini, .opencode) in only 2 of 6
    `Templates` in one tool and `templates` in three others, so the same folder
    was skipped or scanned depending on which tool ran and how the user had
    capitalised it

So this is a shared BASE plus explicit per-tool additions, not one merged set.
Merging outright would have silently widened three tools and thrown away the
intent behind the other two.

Matching is case-insensitive, which is what makes the Templates/templates split
stop mattering. `vault_health.VaultExcludes` remains the user-facing extension
point for `.vault-config.json`; this module is the floor beneath it.
"""

from __future__ import annotations

# Never scanned by any tool. Everything here is machine-owned: version control,
# editor and agent configuration, build output, trash, dependencies.
BASE_EXCLUDE_DIRS: frozenset[str] = frozenset({
    # version control and editor config
    ".git",
    ".obsidian",
    # trash, in both spellings vaults use
    ".trash",
    "_trash",
    # build and export output
    "_export",
    "__pycache__",
    "node_modules",
    # agent config directories. These hold instructions and commands, not vault
    # content, and counting them inflates every result (issue #80). Previously
    # only vault_health and freshness_lint skipped the full set.
    ".claude",
    ".agents",
    ".codex",
    ".gemini",
    ".opencode",
    # note templates. Scanned, they duplicate every real note's structure.
    # Spelled capital-T by the bootstrapper and lowercase by three tools, hence
    # the case-insensitive matching below.
    "templates",
})

# Per-tool additions, kept separate because each encodes a deliberate decision
# about what that tool is for, not an oversight.
EXPORT_ONLY_EXCLUDES: frozenset[str] = frozenset({"excalidraw"})
STATS_ONLY_EXCLUDES: frozenset[str] = frozenset({"raw", "references"})


def excluded_dirs(*extra: str) -> frozenset[str]:
    """The base policy plus any tool-specific additions, all casefolded."""
    return frozenset(d.lower() for d in (*BASE_EXCLUDE_DIRS, *extra))


def is_excluded(parts, excludes: frozenset[str]) -> bool:
    """True when any path component matches, compared case-insensitively.

    `parts` must be VAULT-RELATIVE. Passing absolute parts means an ancestor
    directory outside the vault can match and disable the whole scan, which is
    exactly what happened in vault_health's empty-folder check (B29).
    """
    return any(str(p).lower() in excludes for p in parts)
