# Caring Together / Wiingle

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21359273.svg)](https://doi.org/10.5281/zenodo.21359273)

Research artifact for the manuscript **“Caring Together: Designing a Role-Differentiated Empathic Multi-Agent System Inspired by Peer-Support Principles.”**

The manuscript is currently under review. This repository is a software and prompt artifact only; the submitted manuscript PDF is not distributed here.

This repository contains the source code, role prompts, agent-selection logic, deployment configuration, and validation tests for the role-differentiated empathic multi-agent prototype. It does **not** contain participant conversations, survey responses, interview material, application logs, or credentials.

## Artifact contents

- `app.py` — Flask application, agent roles, prompts, selection rules, and response generation
- `templates/index.html` — research-prototype interface
- `lambda_handler.py` and `template.yaml` — optional AWS SAM deployment entry point and configuration
- `tests/test_app.py` — input-validation and response-generation tests
- `docs/agent-conditions.md` — human-readable agent conditions and selection procedure
- `docs/data-and-ethics.md` — public/private artifact boundary and data-availability statement
- `docs/github-zenodo-release.md` — publication and DOI instructions

## System overview

The system uses three differentiated peer-support roles:

1. **Cognitive** — helps organize thoughts and gently broaden interpretations.
2. **Emotional** — acknowledges and validates the user's emotional experience.
3. **Attitudinal** — encourages expression and helps continue the conversation.

For each turn, the selector chooses one or two agents. Recent selections are considered to reduce repetition. Selected agents generate brief responses while receiving limited conversational context and, where applicable, prior peer-agent responses.

## Local setup

Requirements:

- Python 3.9
- An OpenAI API key compatible with the API version pinned in `requirements.txt`

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `OPENAI_API_KEY` and a long random `FLASK_SECRET_KEY` in `.env`, then run:

```bash
python app.py
```

Never commit `.env` or real credentials.

Chat persistence is disabled by default (`CHAT_STORAGE_BACKEND=disabled`), so a local run does not contact AWS. The interface uses repository-local image assets and does not access an author-owned S3 bucket.

## Cost and cloud-safety notice

Cloning or running this repository does not use the authors' AWS account. No author-owned AWS account ID, endpoint, access key, bucket URL, or credential is included. Users pay their own model-provider charges if they insert an API key.

AWS deployment is optional. Anyone who chooses to deploy `template.yaml` creates resources in their own authenticated AWS account and is responsible for those charges. The template uses a table-scoped DynamoDB policy rather than account-wide access. Authors should not publish a live API Gateway URL from a personally funded deployment; a public endpoint could be abused and generate Lambda, API Gateway, DynamoDB, and model-provider charges.

## Tests

```bash
OPENAI_API_KEY=test-key \
FLASK_SECRET_KEY=test-secret \
AWS_DEFAULT_REGION=ap-northeast-2 \
AWS_EC2_METADATA_DISABLED=true \
python -m unittest discover -s tests -v
```

The tests mock paid model calls and chat persistence.

## Research-data boundary

No human-participant response data are included. See `docs/data-and-ethics.md` for the repository scope and proposed Data Availability Statement.

## Citation and archival DOI

Version 1.0.0 is archived on Zenodo at [https://doi.org/10.5281/zenodo.21359273](https://doi.org/10.5281/zenodo.21359273). Use this version DOI when citing the reviewed artifact.

## License

The software and accompanying repository documentation are released under the MIT License. The license permits reuse but does not grant access to participant data, the submitted manuscript, trademarks, or third-party materials. Anyone who supplies model-provider credentials or deploys cloud infrastructure is solely responsible for charges incurred in their own accounts.
