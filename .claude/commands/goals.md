---
description: Re-orient on sshdd's PRD goals and non-goals before continuing work
argument-hint: [optional focus area, e.g. a feature name or section topic]
---

Read `docs/PRD.md`, specifically its Goals, Non-goals, and Build-Phases sections — however they're titled or numbered in this project's PRD. Check the document's own table of contents or headings rather than assuming specific section numbers.

Restate, in your own words, which goal(s) the current task in this session serves. If the task does not clearly map to a stated goal, flag that explicitly before proceeding — do not silently expand scope.

If `$ARGUMENTS` is provided, narrow this check instead of reading the whole document: search the PRD's headings for a section whose title matches or clearly relates to the given keyword (e.g. an argument of "auth" should match a heading like "Authentication" or "Access Control"), and read that section specifically. If nothing in the PRD's headings plausibly matches the given keyword, say so rather than guessing at an unrelated section, and fall back to reading the whole Goals/Non-goals/Build-Phases set instead.

Do not implement anything in this command — this is a checkpoint, not a build step. End by stating in one sentence what you are about to do next and which goal it serves.
