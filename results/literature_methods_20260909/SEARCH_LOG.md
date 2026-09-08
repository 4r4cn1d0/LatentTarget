# Literature search provenance

Access date: 9 September 2026 in India, 8 September UTC. This is a targeted
methods review, not a systematic review or an exhaustive novelty search.
The user requested other papers while the fixed presentation diagnostic was
running. Its packet, ordering, stopping rules and primary analysis remain frozen.

The paper lookup skill and its full arXiv reference were read. Public arXiv
Atom metadata was retrieved with curl and checked with the skill's
`scripts/arxiv_atom.py` parser. No API credentials or paid literature service
were used. arXiv requests were serial and spaced by more than three seconds.

## Discovery queries

Primary source search used the following queries, followed by publisher or
arXiv full text rather than secondary summaries:

1. FANToM benchmark stress testing machine theory of mind interactions 2023
2. Transformers represent belief state geometry residual stream Shai
3. Large Language Models Fail on Trivial Alterations to Theory of Mind Tasks Ullman
4. language models theory of mind causal interventions mental states 2025 2026
5. site.arxiv.org Towards Best Practices of Activation Patching Nanda
6. site.arxiv.org theory mind representations causal intervention 2025 2026 language models
7. site.arxiv.org Emergent World Representations synthetic task
8. site.arxiv.org theory of mind 2026 causal
9. site.cell.com neuron Daw 2011 model based influences humans choices striatal prediction errors

The initial metadata request was
`https://export.arxiv.org/api/query`, with `max_results=10` and
`id_list=2310.15421,2405.15943,2302.08399,2406.14737,2210.13382,2309.16042,2501.15355`.
It returned seven valid records, with no embedded API error. Later versions
of Shai and SCALPEL were identified in this response and their methods were
checked in those versions, not only the older HTML initially discovered.

A followup metadata download includes the three 2026 papers. The exact query
is preserved in its Atom feed. The raw feed is `arxiv_metadata.xml` in this
directory. ACL metadata was checked at the two linked anthology records.
The parser returned ten valid records. The raw feed SHA256 is
`74e08d7338c51a770c19d948faa5d17fe08b4a37164d0a7e663cc890ff535265`.
It identifies Muchovej v3 and Ackerman v2 as the current versions. Their
unversioned PDF links resolved to full texts, while the final review links pin
these versions explicitly. No numerical result from either is used as an
estimate of our checkpoint's performance.

## Reading scope

The review uses relevant methods, controls and limitations in primary full
texts. It does not claim that every appendix, code release or empirical
result was independently reproduced.

| Paper | Version or venue | Sections checked |
| --- | --- | --- |
| Kim et al., FANToM | EMNLP 2023, ACL 2023.emnlp-main.890 | 3.3 to 3.5, 4 metrics and results |
| Pi et al., SCALPEL | arXiv 2406.14737v2 | Methods, counter hypotheses, discussion |
| Muchovej et al., GPT-4o Lacks Core Features of Theory of Mind | arXiv 2602.12150 | Studies 1 to 3, general discussion |
| Ackerman, Selective Deficits in LLM Mental Self-Modeling | arXiv 2603.26089 | Task, load manipulations, results, limitations |
| Shai et al., Transformers represent belief state geometry | arXiv 2405.15943v3, NeurIPS 2024 | 2, 3.1 to 3.3, 4.4 |
| Li et al., Emergent World Representations | arXiv 2210.13382v5, ICLR 2023 | Probing, 4 interventions, discussion |
| Zhang and Nanda, Towards Best Practices of Activation Patching | arXiv 2309.16042v2, ICLR 2024 | Methods overview, 6 recommendations, 8 limitations |
| Raifer et al., Designing an Automatic Agent for Repeated Language-based Persuasion Games | TACL 2022, ACL 2022.tacl-1.18 | 3 task, model overview, 7 ablations |
| CoSToM | arXiv 2604.10031v1 | 3.1 to 3.2, decoder and supervised LoRA objective |

Ullman 2302.08399 and ToM-agent 2501.15355 were screened using metadata and
abstracts. They are background leads, not counted as full method reviews.
Daw et al. (2011), DOI 10.1016/j.neuron.2011.02.027, was identified but the
PMC page returned a browser challenge and the author PDF failed in the web
reader. No method recommendation here relies on a claimed full reading of it.
The first HTML requests for 2602.12150 and 2603.26089 failed; both PDF full
texts were accessible and used instead. No access control was bypassed.

The studies test different definitions and model versions. An older model's
failure is not evidence that our newer checkpoint lacks the capability. A
paper's use of a term such as causal tracing or theory of mind is not accepted
as proof that it isolates a unique internal psychological representation.
