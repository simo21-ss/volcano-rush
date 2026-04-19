---
description: Split all pending changes into meaningful, separately buildable commits, run tests after each, then push.
---

# Split-commit-push

Take every pending change in the working tree (staged, unstaged, and untracked) and land it as a sequence of meaningful commits. The test suite must pass after **every** commit. Push at the end.

## Procedure

1. **Survey the changes.** Run these in parallel and read every hunk:
   - `git status`
   - `git diff` (unstaged)
   - `git diff --cached` (staged)
   - `git log -10 --oneline` (match commit-message style)

2. **Group into commits.** Partition the changes into the smallest set of cohesive, self-contained commits such that:
   - Each commit tells one story (one bug fix, one refactor, one feature, one doc change, one rename, etc.). Never mix unrelated concerns.
   - Each commit is individually buildable and testable — the repo compiles and `pytest tests/ -v` passes at every commit, not only at the tip.
   - Renames stay together with the smallest edit that makes them coherent; do not split a rename across commits.
   - Doc / notebook / config changes go in their own commits when they are not load-bearing for a code change.
   - If a code change and a test change belong to the same logical unit, they go in the same commit.

   Before staging anything, write the plan as a numbered list of `<commit subject> — <files>` and show it to the user. Do **not** ask for confirmation — proceed immediately with execution — but make the plan visible so the user can interrupt if the grouping is wrong.

3. **Execute each commit in order.** For commit `i`:
   1. Stage exactly the files (or hunks, via `git add -p` equivalents using `git apply` when a file must be split across commits) belonging to commit `i`. Never use `git add -A` or `git add .`.
   2. If any staged file lives under `simulation_engine/` or `tests/`, run `pytest tests/ -v`. If no staged file touches those paths, you may skip the test run for that commit (document it in the plan).
   3. If tests fail, **stop**. Do not commit. Report the failure to the user and wait for instructions. Do not attempt an autonomous fix unless the failure is trivially caused by the staging itself (e.g., you forgot to stage a needed file).
   4. Commit with a concise message matching the repo's existing style (see `git log`). No `Co-Authored-By` trailer (project rule from the code-formatting skill). Pass the message via a HEREDOC to preserve formatting.
   5. Move to commit `i+1`.

4. **Final verification.** After the last commit:
   - Run `pytest tests/ -v` one more time on the final tree.
   - Run `git log --oneline <base>..HEAD` to show the user the resulting sequence.

5. **Push.** `git push`. If the branch has no upstream, use `git push -u origin <branch>`. Do **not** force-push under any circumstance.

## Rules and guardrails

- **Respect the user's work as-is.** Do not modify the content of any pending change while splitting commits: preserve the user's edits, indentation, whitespace, empty lines, trailing newlines, comment style, and formatting exactly as they wrote them. This command only groups and commits existing changes — it never rewrites, reformats, or "cleans up" them.
- Never skip hooks (`--no-verify`) or bypass signing.
- Never amend. Always create new commits.
- Never commit files that look like secrets (`.env`, `*credentials*`, `*.pem`, etc.). If you see one staged, stop and surface it.
- Never `git add -A`, `git add .`, or `git add -u`. Always name files explicitly so unrelated work doesn't bleed in.
- If the tree is clean (nothing to commit), report that and exit.
- If a single change cannot be split without breaking the build (e.g., a rename plus its import fix-ups), keep it atomic — one story, one commit.
- Match the repo's commit-message style observed via `git log`. First line imperative, under ~72 chars.

## Output to the user

- Before executing: print the commit plan (numbered list).
- While executing: one short line per commit (subject + pass/fail of tests).
- After executing: the final `git log --oneline` range and confirmation that `git push` succeeded.
