# Tire fitment explorer

Streamlit display that sits beside the poster for the Fleet Tire Optimization Strategy capstone project at the University of Waterloo. It shows how tire width, rim diameter, tire type, tread depth and pressure change stopping distance, slip and other health and safety indicators in summer and winter.

## Layout

- `tire_model.py`: the model. Lookup tables and pure functions, no Streamlit. `evaluate(cfg, env)` returns every output for one tire setup in one condition.
- `app.py`: the Streamlit page. Sidebar controls, braking animation (HTML canvas in `st.iframe`), tire size picture (SVG drawn to scale, shown with `st.image`), Plotly charts, Simple and Technical views, demo mode.
- `tests/test_model.py`: calibration anchors and sanity checks for the model.
- `tests/test_app.py`: smoke test that the page renders in both views and in demo mode.
- `.streamlit/config.toml`: light theme and minimal toolbar for the hosted version.
- `SOURCES.md`: every published test and reference behind the model, with links, the judgement values with no published support, and the sources that were removed. `NOTICE` and `CITATION.cff` carry copyright, third-party licences and how to cite.

## Commands

- Run: `streamlit run app.py`
- Test: `python -m pytest -q`
- Install: `pip install -r requirements.txt` (`requirements-dev.txt` adds `pytest`)

## Rules for changes

- This is a screening model calibrated to published tire tests, not measured data. Never word UI text as if a number were a measurement of a specific tire.
- Any change to friction tables, exponents or the hydroplaning formula must keep `tests/test_model.py` passing. If an anchor needs to move, cite the test or paper that justifies it in the test docstring, in the "Model and sources" tab and in `SOURCES.md`.
- Only cite sources whose figures have been confirmed. Never add a citation, link or figure to `SOURCES.md` or the model tab that has not been found; if a source cannot be supported, remove it and list the effect under judgement values.
- The repository is public under Apache-2.0. Never name the project client anywhere in the code, the app, the documentation or commit messages, and do not commit client records or fleet lists.
- Authors and copyright holders are Harrison Cormier, Ashley Pacek and Varvara Blinova, equally. The acknowledgement is that the work was conducted at the University of Waterloo. Keep `NOTICE`, `CITATION.cff`, the README, the app footer and the model tab consistent on this.
- Keep the model free of Streamlit imports.
- Keep code simple and readable: plain functions and dicts, no clever abstractions. Explain in prose (docstrings, README, the model tab), not inline comments.
- UI wording is plain language for a poster audience. The Simple view carries no jargon; the Technical view may. The comparison tire is called the "factory tire" in the Simple view and the "reference" in the Technical view; pass `ref_name` rather than hard-coding either word in shared components.
- Chart colours: selected setup is blue `#2a78d6`, reference is grey dashed, a longer braking distance in the one-change-at-a-time chart is dark grey `#52514e`, tire types keep their fixed colours in `COMPOUND_COLOR`. Do not reuse status colours for series.
- Streamlit is pinned in `requirements.txt`. `st.iframe` and `width="stretch"` need a recent version, so do not lower the pin without testing.

## Who does the work, and how it is reviewed

- The main session runs on Opus (`/model opus`) and orchestrates: it plans, decides, reads every change before it is committed, and commits.
- The rule for choosing: hand a task to the cheapest model whose likely mistakes the next check will catch, and keep work whose mistakes no check would show (a number in the model, a citation, authorship). Work with nothing left to decide goes to smaller models through the Agent tool's `model` setting:
  - `haiku` to run the tests or find where something is. The main session trusts the result unless it is surprising or drives an edit, and then reads one cited line.
  - `sonnet` for an edit whose exact rule is already written. The main session reads the whole diff, checks that the new test fails without the change, and runs the tests.
- Each brief says the goal, the files, what done means and what is already known. It asks for every claim with a `file:line` or a command and its output, and it states a claim to test, not a conclusion to confirm. Tasks of three tool calls or fewer are not delegated, because a helper starts cold.
- A helper stopped by a usage limit is resumed, not restarted. The commit or pull request says what was delegated, how it was checked and anything that had to be redone.
- Changes to the model's numbers, the friction tables, the hydroplaning formula, `SOURCES.md` and anything about authorship stay with the main session.
- A review during the work, such as a second opinion on a change to the model, runs on Opus, read-only.
- Fable, the strongest and dearest model, is used for two things only (the owner's instruction, 2026-11-19): the final review of a change before it is merged, and a hard area the main session calls it in for, such as whether a calibration anchor still matches its source. It works read-only and reports back. If Fable is not available, the final review runs on Opus and the commit or pull request says so.
- A reviewer reproduces every finding, by running the tests or a small script, before reporting it.

## Stay in this repository (owner's rule, 2026-11-21)

A session works on this repository only: its folder, its own git worktrees
and its own GitHub repository.

1. **Ask before changing anything else.** Changing another repository, or a
   folder outside this one, needs the owner's approval in the conversation:
   - editing or writing its files;
   - committing, pushing, merging or changing branches there;
   - opening, merging, closing or commenting on its pull requests or issues;
   - changing its settings.
   The approval is for that repository and that change, and does not carry
   over to the next one. Reading anything is fine.
2. **When the work seems to need a change elsewhere,** write it under
   '## Known gaps' in `CLAUDE.md`, and ask. Don't make the change and
   report it afterwards.
3. **Helpers follow the same rule.** A brief never sends a helper to write
   outside this repository.
4. **The guard backs the rule.** `.claude/settings.json` runs
   `scripts/guard_repo_boundary.py` before every file edit and shell
   command. When a call would change something outside this repository,
   the owner gets a permission prompt and decides. The session cannot
   approve it for itself. Scratch space (the system temp folder) stays
   writable, except inside another repository there. The guard catches
   mistakes; it is not a sandbox, so the rule still holds where the guard
   cannot see.

## Demo mode layout

Demo mode is meant to run full screen on a 13-inch laptop with the sidebar collapsed. Its first screen (banner, three metrics, braking animation, verdict and tire picture) must fit in about 800 px of height, with the comparison charts one scroll below. To keep it that short, demo mode hides the page title, drops the heading inside the animation and caps the tire picture height. Check at 1440 x 800 after changing anything above the divider.

Demo mode is dark; everything else is light. `use_dark_theme()` in `app.py` swaps the module-level colour names for the values in `DARK`, and a demo-only style block recolours Streamlit's own text, tables and header. Never hard-code a colour in a component: use the palette names (`PAGE`, `SURFACE`, `PANEL`, `GRID`, `INK`, `INK_2`, `TIRE`, `TREAD`, `BANNER` and the verdict text colours) so both palettes keep working, and check new UI in both. The sidebar stays light because demo mode runs with it collapsed.

## Known gaps

- Vehicle classes in `VEHICLES` are generic placeholders. Replace with the real fleet list and factory sizes when available.
- Price, wear, fuel, wheel weight, ride and damage indices are simple scaling rules. Replace with fleet purchase and service records where the project has them.
- No studded tires, load transfer, ABS tuning or brand differences.
- Standing water and slush are the least calibrated region. When the braking speed is close to the hydroplaning onset, distance becomes very sensitive to tread, width and pressure (for example 6 psi low adding about 55% in slush at 80 km/h). The direction is right; the size has no published anchor yet.
- The quick-fitment buttons pick the nearest 5-point aspect ratio, which is not always a size that is sold.
