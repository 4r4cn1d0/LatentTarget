# GSD workflow support repair

Date: 7 September 2026

## Request and outcome

The user asked to get the GSD workflow files after the experiment design work encountered missing support files. The GSD skills already existed, but their referenced Codex support directory did not.

Restored GSD version 1.42.3 at `/Users/spiderishi/.Codex/get-shit-done`. This includes 282 files, of which 103 are workflow files and 49 are templates. This is a repair of the installed version, not an upgrade to the latest release.

The repair did not run a research experiment, call a model provider, deploy a GPU, edit Google Docs, commit changes, or push to GitHub. The unfinished partner state study draft remains a draft.

## Source verification

The existing Claude support installation was version 1.42.3. All 282 support files matched its local installation manifest. All 100 concrete support file references found in the installed GSD skills existed in that version.

The repair used the [official version 1.42.3 npm package](https://registry.npmjs.org/get-shit-done-cc/1.42.3), whose metadata identifies [gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done) as its repository. The package archive passed its registry SHA512 integrity check. Archive entries were checked for unsafe paths and links before extraction.

Provenance:

| Item | Value |
| --- | --- |
| Upstream version tag commit | `7dfeb7ad8acbd6febd2c8c6cf7d3dcb7d1aeb7b9` |
| Archive SHA256 | `ced3fa71842c857cb5320b847227eb50246481004e365e20fe8edaf2d2a2a52f` |
| Upstream installer SHA256 | `6f70e9f39322319964bdfe331678427e3f6569e92b473d8ecc31f6ffff65d33d` |
| Repair script SHA256 | `74dda598ee1db3979fa54a34c63b2c96f75cb3c19c728c9aced16322ba8c9477` |
| Repair timestamp, UTC | `2026-09-07T14:15:37.264Z` |

The machine specific inventory and SHA256 digest of every restored file are saved at `/Users/spiderishi/.codex/gsd-support-repair-20260907.json`.

## Method and preservation

The full global installer was not run. Its source was inspected, and its exported `populatePristineDir` helper was used in test mode to apply the official Codex path and Markdown conversions in a fresh temporary staging directory. This converted 280 package support files. The version marker and shared model catalog, which the full installer normally adds separately, supplied the remaining two files.

The repair refused an existing destination and moved the completed staging payload into the missing support directory. Existing skills, agents, hooks and settings were not replaced. Hash checks verified that 113 protected files were unchanged.

A temporary repair script initially failed `node --check` because a function was missing its closing brace. This was caught before execution or installation. The brace was fixed, the syntax check passed, and the repair then completed.

## Verification actually run

| Check | Result |
| --- | --- |
| Installed file hashes against saved repair inventory | 282 of 282 passed |
| Node syntax checks for installed JavaScript runtime files | 66 of 66 passed |
| Concrete support references across installed GSD skills | 100 of 100 resolved |
| Protected settings, skills, agents and hooks | 113 files unchanged |
| Version marker | 1.42.3 |
| `gsd-tools.cjs init phase-op 1` in LatentTarget | Exit code 0 with structured JSON |

The restored spec workflow and its template were read completely. An entire GSD phase was not executed, and no agents were spawned.

## Remaining conditions and warning

The command line check reports `planning_exists: false`, `roadmap_exists: false` and `phase_found: false`. LatentTarget does not yet have a `.planning/` roadmap. The `gsd-spec-phase` workflow explicitly stops when a requested phase is absent, so restoring the files does not itself create or complete a project phase. No planning history was invented and no roadmap was created during this repair.

The same check reports missing agents. Source inspection shows that this version's agent presence checker recognizes `.md` and `.agent.md` files but not Codex `.toml` files. All 33 expected agent names have existing `.toml` files in the Codex agents directory. This explains the presence warning but does not establish that agent dispatch works. The pinned upstream checker and existing agent configuration were left unchanged.

## Next

Resume the experiment design using the restored support files. Before invoking a numbered GSD spec phase, establish project planning context from the existing research documentation and preserve every scientific stop condition. The study design, power calibration, semantic validation and approval gates are separate from this tooling repair.
