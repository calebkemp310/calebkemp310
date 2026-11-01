# Instructions for Claude

## MEMORY MANAGEMENT

This repo uses structured memory folders. Treat them as the source of truth for context across sessions.

At the START of each session:
- Read `memory/memory.md` for core context
- Read the relevant files in `workspace/` (projects, preferences, knowledge-base)

At the END of each session (or when meaningful work is finished):
- Update `memory/memory.md` with key takeaways
- Update the relevant workspace files with new decisions, progress, or information
- Keep files concise: remove outdated info
- Commit the memory updates along with the work

NEVER duplicate information across files — each fact lives in one place.
ALWAYS prefer updating existing entries over adding new ones.

## Layout

```
memory/memory.md                       agent's core memory (summary + pointers)
workspace/projects/goals.md            what's being built & why
workspace/projects/decisions.md        choices already made (dated, with reasoning)
workspace/projects/current-status.md   where things stand now
workspace/preferences/coding-style.md  formatting, naming, conventions
workspace/preferences/communication.md how Caleb wants responses
workspace/knowledge-base/research-notes.md  gathered information
workspace/knowledge-base/reference-data.md  key reference material
```
