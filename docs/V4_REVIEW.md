# V4 adversarial engineering and scientific review

Date: 2026-09-01

Verdict: **ready for the frozen paid preflight; no real-model V4 claim exists
yet**.

The packaged GSD review workflow was unavailable because its referenced local
workflow files were missing. This review therefore used the same fail-closed
criteria directly against code, tests, manifests, prompts, and generated local
artifacts.

## Resolved before launch

| severity | finding | resolution and evidence |
|---|---|---|
| high | Reward and primary measurement shared language-scoring vocabulary in V3 | V4 target and outcome use immutable registered candidate frame IDs; no language scorer is on the causal path |
| high | A field named `visible_history` retained hidden frame labels even though the prompt renderer ignored them | The visible projection now contains only fields actually rendered; mock-only ground truth has a separate method; schema/audit/regression tests reject reintroduction |
| high | A long resumed run could change top-p, dtype, thinking, capture, or provider while preserving only the basic config | Resume now compares the full immutable provider contract and rejects drift |
| high | Manual CLI flags could accidentally launch a different model, sample, target, or decoding configuration | The real runner reads the frozen JSON and runs a pre-generation plan audit; an exact dry run passes and a 19-seed drift test fails before model loading |
| high | A crash could force a complete restart or lead to duplicate data | Completed episodes are appended once, progress manifests are updated, and resume validates complete round sequences, duplicate keys, known episode IDs, config, and provider settings |
| medium | Logged history for elicited trials showed probabilities without preserving the candidate texts they referred to | Each prior candidate and estimate is now rendered and logged together |
| medium | Progress output could expose partial choices and invite outcome monitoring | Real-run progress reports completion only; analysis is deferred until the completed manifest reports 7,200 rows |
| medium | Model repository drift could silently change weights | Model ID and immutable Hugging Face revision are checked in preflight, planned run, and final manifest audit |
| medium | Message-bank labels were researcher assertions | Two blind machine judges saw only opaque IDs and text; both classified 90/90 correctly and agreed perfectly; exact inputs/outputs are retained |
| medium | Power could count rounds as independent observations | Simulation and final tests use episode summaries; rounds form five-observation windows within episodes |
| medium | Mock success could be mistaken for model evidence | Manifests, summaries, decisions, and docs label mock results implementation-only; a mock pass cannot set `scientific_pass=true` |

## Open scientific limitations

1. The controlled-choice task is cleaner but less ecological than free-form
   generation. A positive result must later replicate with spontaneous text.
2. Candidate frames and target response types are synthetic and categorical.
3. The manipulation check is machine-only; it is strong enough for this
   registered-candidate primary measure, but not evidence about human
   persuasion.
4. The 20-seed choice relies on a declared normal approximation to the final
   sign-flip tests and on effect-size assumptions. Sensitivity curves are
   reported; the run must not be called well-powered for effects smaller than
   those simulated.
5. Behavioral success cannot distinguish an explicit target representation
   from a compact reinforcement or win-stay/lose-shift policy. That distinction
   requires a separately specified mechanistic stage.
6. The confirmatory checkpoint covers one current dense open-weight model and
   one greedy decoding configuration. Generalization requires preregistered
   replications, not post-hoc model shopping.
7. Candidate messages contain stylized fairness, safety, and authority claims.
   The result concerns response-policy learning in this constructed task, not
   ethically effective real-world persuasion.

## Launch recommendation

Commit and push the clean pre-data state. On the GPU host, verify that exact
commit, run all tests, run only the one-generation V4 preflight, and proceed to
the 7,200-row checkpoint only if the preflight passes. Do not capture
activations, run elicited diagnostics, inspect partial metrics, or change a
frozen value during the checkpoint.
