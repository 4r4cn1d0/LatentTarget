# Fixed history bank audit

All 36 frozen evaluation bundles. No new model calls or history draws.

This supplementary audit was specified after the three bundle pilot. It is descriptive, not confirmatory.

Participant evidence categories (n = 72): {'uniquely_correct': 46, 'tie_includes_true': 16, 'wrong_best_type': 10}.

| Policy | Familiar regret | Composite regret | Paraphrase regret |
| --- | ---: | ---: | ---: |
| original_jaccard | 0.00979 | 0.04987 | 0.05767 |
| content_jaccard | 0.03029 | 0.05276 | 0.06102 |
| stem_jaccard | 0.02827 | 0.04996 | 0.08253 |
| character_trigram | 0.01108 | 0.03783 | 0.06125 |
| length_only | 0.09942 | 0.05819 | 0.11382 |
| static_belief | 0.00000 | 0.00000 | 0.00000 |
| participant_feature_reward | 0.00000 | 0.00684 | 0.00000 |
| typed_history_oracle | 0.02978 | 0.02066 | 0.02978 |

Regret uses the static reference assumptions and privileged frame annotations. It is not a measured target success rate.
Zero for the static belief reference is a computational consistency check, not an empirical discovery.
The hidden type oracle knows the actual generator, not just the available history. It can disagree with this evidence based objective.
All participant posteriors, bundle values and reference choices are retained in summary.json. No histories were dropped.
