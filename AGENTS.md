# Arciv

## Project Description
My personal portfolio website.

## Context

This is a solo project; no other developers read or maintain this code. That means:

- No one will explain what "clever" code does when you've forgotten. Write for the version of
  yourself 6 months from now.
- No PR reviews catch mistakes. Lean on type hints, explicit naming, and logging to compensate.
- Refactoring is cheap (no coordination cost), but debugging is expensive (no one to ask).

## Coding Principles

**Maintainability over elegance.** If it takes more than 10 seconds to understand what a line does,
rewrite it. "Clever" is not a compliment.

**Abstractions must earn their keep.** Every new class, pattern, or indirection must justify its
existence with a concrete benefit. "It's more elegant" is not justification.

**Debuggability is a feature.** When something breaks, can you figure out why from the error message
and a stack trace? Can you inspect intermediate state? If not, add logging or simplify the control
flow.

**Prevent, don't post-process.** Fix data quality problems at the source (e.g. configure trafilatura
to exclude code blocks) rather than writing complex cleanup logic downstream.

**Boring and correct beats clever and fragile.** The best solution is the one that obviously works,
not the one that impressively almost works.

## Code Standards

✅ **Always do:**

- Type hint all function parameters and return types. Prefer builtin types (`list`, `dict`) over
  `typing` module types (`List`, `Dict`).
- Use Google docstring style.
- Raise specific exceptions with context.
- Put regex patterns in constants with the `_RE` suffix (e.g. `DATE_RE`).
- When adding imports in `__init__.py`, add to `__all__` as well.
- Use relative imports within the same module.
- Use `pathlib` over `os` for file paths.

⚠️ **Ask first:**

- Adding dependencies beyond core stack
- Changing the SQLite schema
- Modifying URL processing rules or rewriters
- Changing scraping/conversion pipeline flow

🚫 **Never do:**

- Skip type hints on functions
- Hardcode file paths
- Use lazy imports inside functions
- Add `*args` / `**kwargs` without a specific need
- Use premature abstraction, design patterns for their own sake, or metaprogramming where a simple
  function would do

# Formatting requirements
Avoid the stylistic tics common to LLM output. Don't inflate importance: skip phrases like "stands
as a testament to", "plays a vital/pivotal/crucial role", "rich tapestry", "vibrant", "underscores
its significance", or claims that some mundane detail "reflects a broader" trend. Don't tack
present-participle commentary onto sentence ends ("..., highlighting its impact", "..., cementing
its legacy"). Cut the recurring vocabulary: delve, boasts (meaning has), showcase, foster, robust,
meticulous, landscape (figurative), realm, nestled, leverage. Don't overuse the rule of three or
"not only X but Y" / "it's not just X, it's Y" parallelism. Prefer plain verbs (wrote, not authored;
used, not utilized; has, not features). Use straight quotes and apostrophes, no em-dashes, no curly
quotes. Don't end with a "Conclusion" or "In summary" restatement, and don't add a "Despite its
challenges..." wrap-up. Don't pad with hedges ("it's important to note", "it's worth mentioning").
Don't add knowledge- cutoff or "based on available information" disclaimers. Don't over-bold, don't
turn every list item into "**Bolded label**: explanation", and don't put every section in Title
Case. Match length and formality to the task; default to fewer words, concrete specifics over
generic praise, and a real voice over a neutral encyclopedic hum.

For generated code: don't docstring or comment trivial functions; comment only where logic is
non-obvious. Use specific, contextual names, not generic data/result/temp/process_data. Add error
handling only where a failure can actually occur; never wrap everything in broad try/except that
swallows exceptions. Don't over-engineer: no repository patterns, abstract base classes, factories,
or dependency injection for problems that don't need them. Prefer stdlib over pulling a library per
sub-problem; don't grow the dependency list unnecessarily. Clean up after iteration: remove dead
code, unused functions, and orphaned imports rather than leaving them. Calibrate structure to the
actual requirement instead of applying "best practice" boilerplate by default.
