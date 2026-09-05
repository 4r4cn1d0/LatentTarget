# Google Docs revision log

## Destination and access

- Updated the existing [Latent Target Writeup](https://docs.google.com/document/d/1n42djKj_BI6uJdwVk2bNp-0n1fIrwgjdv_AmNqIGBUo/edit), tab `t.0`, in place.
- The initial write failures were caused by an account mismatch. The user granted the connected account Editor access. The connector then successfully wrote to the original document.
- Did not create a replacement Google Doc or change general sharing permissions.

## What changed

- Replaced the old executive summary with a more direct account of the question, setup, result, failed revision test, limitations, and next steps.
- Added the detailed report behind the summary: methods, three exact system prompts, results, failed redesigns, AI assistance, audit notes, fourteen seeded round examples, and reproduction links.
- Preserved the existing overview image and inserted seven additional figures from the project files. All eight figures have captions. The narrative table that repeated the failed design descriptions was consolidated into the surrounding prose, with its distinct design details retained.
- Applied the user's writing preferences: a personal, question led narrative, shorter explanations around technical claims, fewer unnecessary hyphens, and no em dashes. Recorded the punctuation rule in `docs/WRITING_VOICE.md`.
- Kept exact model identifiers, prompts, candidate messages, and model outputs rather than rewriting experimental evidence as narrative prose.

## Scientific corrections

- The positive Qwen result is described as behavioural learning in this controlled task, not proof of a latent partner representation.
- The swap result failed the registered revision test. Its asymmetry is consistent with default attraction but does not establish that mechanism.
- The reworded prompt produced a positive estimate but failed the validity gate. Failures affected 10.2% of all rounds and depended on history condition. Random fallback is not described as an automatically harmless dilution, and parsed records are not presented as an unbiased correction.
- Choices maximising stated probabilities do not prove that probability vectors and choices contain identical information. The belief arm also changed prediction history, so it cannot isolate elicitation alone.
- Null results and simulated positive controls do not establish that a capability is absent or that every aspect of the measurement is sound.
- Clarified that the Gemma bars in the default frame figure use the V5 bank, separately from the R1 replication.
- Replaced the unconfirmed claim that all gates and readings were personally authored with an explicit account of AI contributions to coding, experiments, design, and writing.
- Distinguished per arm frozen specifications from a claim that the entire evolving project was preregistered at once.
- Removed an unsupported current GPU cost estimate and did not promise that proposed redesigns would fix the problem.

## Verification actually performed

- Native connector readback confirmed the correct document and its original single tab, eight inline images, native headings and lists, and eight source hyperlinks.
- Text checks found zero em dashes and zero `[CONFIRM` markers. All three system prompt blocks were present, and fourteen model output examples were retained.
- Exported the live Google Doc and inspected every rendered page. Fixed inconsistent fonts, split examples, prompt spacing, and a stranded audit bullet.
- The final export is eighteen pages. After the last local formatting repair, the changed audit page was inspected again. The other seventeen rendered pages were byte identical to the corresponding pages already inspected.
- The official ICML workshop page was checked for the Chen et al. reference. The linked OpenReview page required browser verification, so the document uses the accessible official ICML listing rather than claiming a new full paper review.
- No new experiments or paid compute were run. The test suite was not rerun. The report explicitly labels 793 passing tests as the last recorded run, not a test executed during this edit.

## Artifact status

The live Google Doc is the revised deliverable. Earlier locally generated Word and PDF drafts were not regenerated in this pass and should not be treated as identical to the current Google Doc. Connector readback receipts and rendered QA pages are retained under `tmp/google-docs/`. This log and the writing preference update have not been committed or pushed in this turn.

## Follow up: natural prose and typography

The user requested a further pass for natural wording, their own voice, and consistent formatting. The live Google Doc was edited in place through 54 targeted text replacements, followed by typography and pagination repairs.

### Changes

- Used `docs/WRITING_VOICE.md` as the voice reference. Replaced stiff framing, repeated caveats, and technical shorthand with direct explanations. Split dense results paragraphs so each paragraph has a clearer purpose.
- Shortened headings, removed the crowded technical note from the byline, corrected the broken phrase in the conclusions, and put the proposed next experiments in a coherent order.
- Kept the substantive scientific limitations, negative results, unfinished human labels, and candid AI assistance disclosure. This was a prose edit, not an attempt to conceal how the project was produced.
- Set the title to bold 18 pt and the byline to 10 pt. Retained 12 pt Times New Roman body text, 16 pt main headings, 14 pt subheadings, 10 pt italic captions, and the compact 11.5 pt audit appendix. Used 10.5 pt Courier New for the exact prompt blocks.
- The first export exposed a prompt split across pages and a mostly empty page before Appendix A. Kept each prompt with its introduction, corrected prompt indentation, and removed the unnecessary page break before the audit appendix. The repaired export returned to 18 pages.

### Verification

- Fresh native readback confirmed the original document and tab, all eight figures, and all eight source hyperlinks.
- Compared the exact prompt text and the fourteen raw round examples with the initial live snapshot. None was changed.
- Confirmed zero em dashes. Hyphens in exact model names, identifiers, and raw experimental text were preserved.
- Exported the final native Google Doc and visually inspected all 18 rendered pages for fonts, sizing, clipping, captions, headings, and page breaks.
- The final saved revision was `ANLCKQkstrJo7c5QWsOb1-aFXJCy6gwlrvBx5ymz5NCz2KvZY8XI3Gr3QpljeIc3ZaNjLRQEdBcQXuV_bCQ3sEK3aOxi5tmeh8kvkZcW7PA`.
- The final trusted read is in `tmp/google-docs/trusted-read-natural-final-20260905/`. Its annotated text has SHA256 `51e19cac04fff2d27ae769955cdbabce774942ff0b6d12cc830270cd163321d1`. The final page renders are in `tmp/google-docs/render-natural-final-20260905/`.
- No experiments, paid compute, test suite runs, commits, pushes, permission changes, or submissions were performed in this pass.

The writing and Docs skills guided a clearer argument and preservation of exact evidence. The PDF skill was used only to inspect the Google Doc export. No claim is made about AI detector scores or an exact, measurable reproduction of the author's voice.
