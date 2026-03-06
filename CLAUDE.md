# CLAUDE.md

## Non-Negotiable Rules
- Ask clarifying questions BEFORE writing any code or making changes
- YAGNI: never add features, comments, abstractions, or error handling beyond what is asked
- Skill-first: invoke a matching skill before acting (see superpowers skills list)
- Hook-first: check .claude/hooks/ for an existing hook; create one if a task will repeat
- Token efficiency: point to context files, never duplicate content inline

## File Size Limits
- CLAUDE.md: 50 lines max
- Context files: 80 lines max each
- Memory/MEMORY.md: 200 lines max (system-enforced)

## Context Files (load only when relevant)
- Stack & tooling → .claude/context/stack.md
- Code conventions → .claude/context/conventions.md
- MCP servers → .claude/context/mcp.md

## Hooks
- Location: .claude/hooks/
- Before creating new code, check if a hook already handles it
- If a task is repeated 2+ times manually, create a hook

## MCP Servers
- Catalogue in .claude/context/mcp.md
- Add a server only when it replaces token-heavy manual steps

## Memory
- Persistent memory at: memory/MEMORY.md
- Topic files: memory/<topic>.md, linked from MEMORY.md
- Do not write speculative or session-specific content to memory
