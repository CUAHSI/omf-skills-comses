# AGENTS.md — OMF Skills Repository

Agent instructions for working in this repository. Every AI agent should read this file before creating, editing, or reviewing skills.

---

## Preferred Commands

Use documented `make` targets whenever possible.
Do not invoke underlying tools directly when an equivalent `make` target exists.

Before submitting changes, run:

```
make validate
```

This is the repository's canonical validation command. It runs the same checks as CI inside the supported container, so `make validate` is authoritative.

Discover available targets with:

```
make help
```

---

## Agent Guidance

Coding agents working in this repository MUST:

- Prefer documented `make` targets for validation, lint, format, test, and clean operations.
- Treat the `Makefile` as the repository's public API and stable interface.
- Run `make validate` before considering work complete.
- Use `make help` when discovering repository capabilities.

Coding agents SHOULD NOT:

- Invent validation, lint, formatting, or container commands.
- Bypass documented workflows with ad hoc shell commands.
- Call `docker`, `python`, `pytest`, `npm`, or similar tools directly when a `make` target exists.
- Duplicate CI logic in one-off terminal commands.

The only exception is when modifying the `Makefile` or container configuration itself, where direct tool invocation may be required to verify the change.

---

## Commands allowed without approval

Agents may run the following commands without asking the user first. They only read state from the repository, GitHub, or Jira, or update remote-tracking refs (`git fetch`); they never change the working tree, commits, remotes, pull requests, or work items.

### Git

- `git status`
- `git fetch`
- `git log`
- `git show`
- `git diff`

### GitHub (`gh`)

- `gh pr view`
- `gh pr list`
- `gh pr diff`

### Jira (`acli`)

- `acli jira workitem view`
- `acli jira workitem search`

### Usage rules

Any flags and arguments are allowed, as long as they keep the command read-only (for example, no `git diff --output=<file>` and no `gh pr view --web`). To keep the terminal from opening an interactive pager, write `git --no-pager log`, `git --no-pager show`, and `git --no-pager diff`, prefer `git --no-optional-locks status`, and prefix `acli` commands with `PAGER=cat`.

Every other command, including any that commits, pushes, rewrites history, or modifies GitHub or Jira, follows the normal approval flow.

---

## Agent handoffs

When a task spans multiple agent sessions or requires explicit transfer of context, place concise handoff notes under `docs/handoffs/`.

Handoffs are transient working documents, not project artifacts. Archive or remove them when no longer needed.

## Repository design principles

The repository prioritizes methodological correctness, transparency, reviewability, and maintainability. It exists to encode community methodological knowledge that foundation models do not consistently possess, not generic software engineering or modeling advice.

As foundation models improve, this repository should become smaller, preserving only frontier community knowledge, standards, workflows, and practices that models do not consistently execute.

## Audience and prose

- Write reports, templates, and explanatory documentation for the people who will read and use them. Use plain language and explain necessary technical terms. Remove coding-agent shorthand that does not help the reader.
- Write `SKILL.md` instructions for agents carrying out a task. They may be more compact and procedural, but must remain clear, specific, and readable by human maintainers. Do not use jargon merely to save words.
- When a file serves both audiences, put the operational rule in `SKILL.md` and use direct, reader-facing wording in the output template. Avoid repeating the same guidance in both files.

---

## Required authoring reference (load when editing skills)

When creating, modifying, or reviewing a skill, you **must read**:

```
docs/agent-skills-creation-reference.md
```

Use it as the canonical guide for `SKILL.md` structure, frontmatter, description optimization, scoping, progressive disclosure, and evaluation.

---

## Editing heuristics

- Preserve routing boundaries.
- Remove redundancy aggressively.
- Prefer composition over duplication.
- Keep guidance proportional to its value.
- Justify consequential methodological recommendations.
- Add references only when they materially support new guidance.
- Preserve traceable intermediate artifacts.
- Every instruction competes for context. If an agent would consistently succeed without it, remove it.

---

## Scope discipline

Each skill should own a single methodological responsibility. Avoid duplicated guidance; overlapping functionality should route to the specialist skill instead of being copied. Many small composable skills are preferred over fewer comprehensive ones.

---

## Skill loading model (critical)

Agents load skills in stages:

1. Discovery → name + description
2. Activation → full `SKILL.md`
3. On-demand → `references/` and `scripts/`

Implications:

- Weak descriptions prevent activation.
- `SKILL.md` must work without references unless explicitly invoked.
- References must include clear load conditions.

---

## Skill anatomy

```
skills/<kebab-case-name>/
├── SKILL.md          ← required: YAML frontmatter + agent instructions
├── assets/           ← output templates and starter files
├── references/       ← normative checklists, standards, compressed artifacts
└── scripts/          ← deterministic automation helpers
```

Rules:

- Folder name **must** match the `name:` frontmatter field exactly.
- Keep `SKILL.md` as small as practical; move detail to `references/` when it improves readability or reuse.
- All paths must be relative.
- No secrets, absolute paths, or personal configuration.

---

## Repository conventions

- **Naming**: `kebab-case` by default
- **Artifacts**: `kebab-case.md`
- **Scripts**: `snake_case.py`, `kebab.sh`
- **References**: `UPPERCASE-TOPIC.md`
- **Config/Templates**: YAML or JSON only
- **Development stability**: `experimental`, `evolving`, `stable` (development
  and compatibility status only)
- **Evals**: ≥3 trigger + ≥3 non-trigger cases
- **License**: MIT default

---

## Evaluation strategy

Each skill must include an evaluation JSON defining trigger and non-trigger
cases.

**Required behavior**: Test with and without the skill using realistic prompts
and artifacts. Compare observed criterion satisfaction, efficiency, and failure
modes across the recorded model, runtime, suite, and inputs.

## ⚠️ Gotcha: calibrated transparency, not implied surety

Skill review and evaluation are empirical, incomplete, and dependent on the
model, runtime, grader, prompts, artifacts, and scientific context. Skill
evaluation remains a dark art and may never be fully vettable. Pursue the
strongest practical scientific rigor and transparency, but never present a
recent review, passing evaluation, validation command, or `stable` label as a
guarantee, certification, or proof of scientific correctness or future
behavior. Strong claims about directly observed process facts remain
appropriate: prefer “On `<date>`, under `<model/runtime/suite/inputs>`, criteria
`<A–C>` were observed as satisfied” over “the skill passes” or “the skill is
validated.”

Report what was examined, by whom, when, under which exact conditions, what was
observed, and what remains uncertain. Use pass/fail only for explicitly named
criteria. For an in-scope criterion lacking evidence, report `unknown` or `not
assessed` with the reason. Label relevant findings outside the named criteria as
exploratory observations; do not silently omit them or let them alter pass/fail
unless the criteria are explicitly revised. Treat review or evaluation age as
a reason for renewed scrutiny, not as proof that guidance is either correct or
obsolete. Treat `stable` as a development and compatibility commitment, not an
epistemic status.

Scope every review or evaluation claim to the `subject-revision` containing the
behavior-affecting skill content. Recording or updating that claim changes the
`record-revision`, not the `subject-revision`; do not make the stewardship
record part of the content identity it describes. Follow
[`docs/skill-stewardship-contract.md`](docs/skill-stewardship-contract.md#revision-identity)
rather than inventing another revision scheme.

---

## Agent skills

### Issue tracker

Tickets live in Jira (project `CAM`, under Objective `CAM-209`, labels `COMSES,OMF-Skills`) via `acli`; GitHub `CUAHSI/omf-skills-comses` is for source code and PRs only. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary, applied as Jira labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout (one `GLOSSARY.md` + `docs/adr/` at the repo root). See `docs/agents/domain.md`.

---

## Key documentation

- `docs/agent-skills-creation-reference.md`: Canonical skill design + specification guide.
- `CONTRIBUTING.md`: Contribution workflow.
- `docs/SKILL-TEMPLATE.md`: New skill template.
- `docs/VALIDATION.md`: Validation rules.
- `docs/roadmap.md`: Planned skills.

---

## Review checklist

- Does this duplicate another skill?
- Does this belong in another skill?
- Should this live in `references/` instead?
- Is routing still unambiguous?
- Can wording be shorter?
- Does the change justify its context cost?
- Does it improve reviewability?

---

## Common mistakes

- No `template/` directory exists. Copy an existing skill.
- `name:` does not match folder name.
- Weak descriptions prevent triggering.
- Publishing `.github/skills/update-skill/`.
- Duplicating large guidance into `SKILL.md` instead of using references.
- Extending a skill when routing to a specialist skill is more appropriate.
