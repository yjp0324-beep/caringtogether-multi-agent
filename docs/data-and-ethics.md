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

> The source code, prompts, and system configuration used to implement the role-differentiated multi-agent system are publicly available at [REPOSITORY DOI]. The authors do not have permission to share the participant data; therefore, conversational data, survey responses, interview materials, and other participant datasets are not publicly available and are not included in this repository.

This wording follows the submitted manuscript's statement that the authors do not have permission to share data. Any later change must first be verified against the approved ethics protocol and participant consent form.

## Pre-publication privacy check

- Search the complete repository history, not only the latest files, for credentials and participant information.
- Confirm that `.env`, database exports, logs, notebooks with outputs, and build directories were never committed.
- Revoke the previously exposed OpenAI key even though it is absent from this package.
- Confirm that no author-owned S3 URL, API Gateway endpoint, AWS account ID, or cloud-resource identifier remains.
- Review screenshots and binary assets for names, messages, metadata, or identifiable content.
- Obtain approval from the principal investigator or institutional data steward where required.
