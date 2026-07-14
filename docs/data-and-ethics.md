# Data, privacy, and ethics

## Included in this public artifact

- application and deployment source code;
- role prompts and agent-selection rules;
- interface code;
- dependency versions;
- tests and reproduction instructions.

## Explicitly excluded

- participant conversation logs;
- raw or processed survey responses;
- interview transcripts or recordings;
- identifiers and demographic records;
- DynamoDB exports, server logs, and local caches;
- API keys, session secrets, AWS credentials, and deployment outputs.

The repository must not be interpreted as a public release of the human-participant dataset.

## Proposed Data Availability Statement

> The source code, prompts, and system configuration used to implement the role-differentiated multi-agent system are publicly available at [REPOSITORY DOI]. Due to the sensitive nature of the conversational data and participant privacy considerations, the participant datasets are not publicly available. Subject to the scope of participant consent, institutional ethics requirements, and an appropriate data-sharing agreement, eligible data may be available from the corresponding author upon reasonable request.

The authors should confirm this wording against the approved ethics protocol and participant consent form before using it in the manuscript. If those documents do not permit external sharing, remove the final sentence and state that the participant data cannot be shared.

## Pre-publication privacy check

- Search the complete repository history, not only the latest files, for credentials and participant information.
- Confirm that `.env`, database exports, logs, notebooks with outputs, and build directories were never committed.
- Revoke the previously exposed OpenAI key even though it is absent from this package.
- Confirm that no author-owned S3 URL, API Gateway endpoint, AWS account ID, or cloud-resource identifier remains.
- Review screenshots and binary assets for names, messages, metadata, or identifiable content.
- Obtain approval from the principal investigator or institutional data steward where required.
