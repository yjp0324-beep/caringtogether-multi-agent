# Agent conditions and selection procedure

This document summarizes the implemented experimental conditions. The exact Korean system prompts are preserved in `app.py` so that the artifact reflects the language used by the prototype.

## Role conditions

| Condition | Primary function | Interaction style | Intended distinction |
|---|---|---|---|
| Cognitive | Organize thoughts and explore reasons behind feelings | Calm, conversational, gently analytical | Broadens interpretation without becoming directive |
| Emotional | Recognize and validate emotion | Warm, concise, non-solution-oriented | Prioritizes emotional acknowledgement |
| Attitudinal | Encourage expression and continuation | Open, supportive, gently inquisitive | Helps the user elaborate at their own pace |

Shared constraints include short one- or two-sentence responses, informal Korean speech, no visible internal role label, and reduced duplication across agents.

## Selection procedure

1. The user's message is provided to a model-based selector.
2. The selector proposes one or two roles as a JSON array.
3. Unknown role names are removed.
4. Recent role history is used to reduce repeated selections.
5. If all candidates are removed, the candidate pool is restored to guarantee at least one response.
6. Candidate order and the final selection count are randomized within the implemented constraints.

The production endpoint independently validates that a client-supplied selection contains one or two unique, known roles.

## Response procedure

Each selected role receives:

- its role-specific Korean prompt;
- up to ten recent conversation entries;
- the current user message;
- available responses from previously executed peer agents; and
- instructions to avoid repeating prior responses.

Responses are limited to 200 generated tokens and post-processed to remove internal role prefixes and retain at most two completed sentences.

## Reproducibility notes

Model outputs remain stochastic because response generation uses a nonzero temperature. Exact text may also vary with provider-side model revisions. Researchers should record the execution date, model identifier, dependency versions, and random seed strategy for each replication.
