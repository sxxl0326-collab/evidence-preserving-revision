# Evidence-preserving revision

Code and numeric analysis inputs for **Evaluating Evidence-Preserving Revision in Collaborative Synthesis**.

Run `python reproduce.py` with Python 3.10 or newer. The analysis uses the standard library, runs offline, and resamples the 25 incidents with both seeds kept together. It reproduces the generic decision–repair gap, the planned relation-selection contrast, and the add-on verification contrast under the end-to-end convention. Semantic disagreements remain unresolved. Output-contract failures are counted as technical failures.

| Comparison | Bounds (percentage points) | 95% paired incident-bootstrap envelope |
| --- | ---: | ---: |
| Generic decision–repair gap | 46 to 54 | 30 to 70 |
| Relation flat minus generic | −14 to +4 | −26 to +20 |
| Generic plus verifier minus generic | −8 to −2 | −16 to +4 |

`workflow.py` implements source-card construction, the four review workflows, the shared coordinator response contract, and the extra verification pass. Provide a callback that accepts a request and returns a parsed structured response, two canonical source objects with distinct paragraph IDs, and a statement. First call `handoff(callback, sources, seed)`, then pass its returned cards to `workflow(callback, sources, cards, statement, arm, seed)`. Supply `verify=True` with `arm="generic"` to add the extra call. The module does not make network requests or run a model by itself. The portable workflow covers the scientific handoff and output contract. Machine-specific measurement, power controls, and logging used during the original study are outside this release.

- `data/prompts.json` contains the exact archived system prompts and model options. The seed and response IDs are set at runtime.
- `data/attempts.json` contains de-identified attempt-level decisions, semantic consensus fields, and whether the paired verifier wording was identical. One incident comprises two seeds and two input polarities. The labels were supplied by assistant reviewers.
- `data/cost_and_defects.json` contains the observed token totals and defect counts behind Figure 3. Defect tags are available for the original four workflows.

The public files omit source text, generated statement text, and individual reviewer responses. The archive reproduces analysis from the observed outcomes. Running new inference requires separately supplied source packets and model execution.
