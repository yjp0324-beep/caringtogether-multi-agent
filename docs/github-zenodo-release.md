# GitHub and Zenodo release procedure

## 1. Complete repository metadata

Before uploading, add:

- final repository title;
- all authors in publication order;
- affiliations and ORCID identifiers;
- corresponding-author contact information;
- funding and acknowledgement information;
- the chosen license;
- a `CITATION.cff` file containing the final manuscript metadata.

Do not invent or approximate author metadata. It should match the submitted manuscript.

## 2. Final local audit

Run the tests and search for secrets:

```bash
python -m unittest discover -s tests -v
git grep -n -E 'sk-[A-Za-z0-9_-]{20,}|password|secret|participant|email'
git status --short
```

Review every match manually. Words such as `secret` can appear safely in configuration examples, but real values must not.

## 3. Create the GitHub repository

1. Create a new public repository under the research group or corresponding author's account.
2. Upload only the contents of this public-artifact folder.
3. Confirm `.env`, `.aws-sam`, `.venv`, caches, logs, and participant data are absent.
4. Enable branch protection if the repository will accept future changes.
5. Add a short repository description and manuscript keywords.

## 4. Connect GitHub to Zenodo

1. Sign in to Zenodo using the GitHub account that controls the repository.
2. Open Zenodo's GitHub integration page.
3. Enable archiving for this repository.
4. Return to GitHub and create a release such as `v1.0.0`.
5. Zenodo will archive that release and mint a version-specific DOI.
6. Check the Zenodo record's title, authors, affiliations, abstract, keywords, license, and related identifiers.
7. Reserve the DOI before the final release if the DOI must appear in the manuscript in advance.

Use the version DOI to cite the exact reviewed artifact. Zenodo also provides a concept DOI that points to all versions; retain both in the project records.

## 5. Update the manuscript and repository

Replace `[REPOSITORY DOI]` in the Data Availability Statement with the final DOI. Add the DOI badge and citation instructions to `README.md`, then create a corrected release if those changes must also be archived.

## 6. Suggested first release description

> Initial research-artifact release accompanying “CaringTogether: Designing a Role-Differentiated Empathic Multi-Agent System Inspired by Peer-Support Principles.” This release includes the prototype source code, role prompts, agent-selection rules, deployment configuration, and validation tests. It excludes all human-participant conversational and survey data.
