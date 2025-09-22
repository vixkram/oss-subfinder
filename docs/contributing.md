# Contributing Guide

Thank you for helping improve oss-subfinder! This document captures the expectations and workflow for contributors.

## Ground Rules

- Treat this project with the same care you would a production service. Security, privacy, and rate limiting are not optional.
- Keep pull requests scoped. Large redesigns benefit from an issue or design doc first.
- Prefer discussing interface changes (API, streamed payloads) before implementation — consumers depend on stability.

## Workflow

1. Fork the repository and branch from `main`.
2. Run `make test` before opening a PR. Add or update tests when you touch critical code paths.
3. For frontend work, run `npm run build --prefix frontend` (or the dev server) to ensure assets compile.
4. Document new configuration options, environment variables, or manual steps in the README and relevant docs.
5. Reference any related issues in the PR description and list the validation steps you performed.

## Style Notes

- **Python**: target 3.10, follow PEP 8, and annotate functions with type hints. Async-first design is preferred for network I/O.
- **React**: functional components with hooks, PascalCase filenames, Tailwind utility classes where practical.
- **Commits**: present tense (`Add rate limiting guard`) and ≤72 characters in the subject line.
- **Logging**: leverage structured logging (already configured for JSON) and avoid leaking secrets.

## Testing Tips

- Use `make test` locally or `docker-compose run --rm backend pytest` if Postgres needs containerized setup.
- When adding async tests, mark them with `@pytest.mark.asyncio` and use fakes/mocks for external services.
- Browser-visible changes should include manual verification notes until an automated suite exists.

## Security & Responsible Use

This project is intended for legitimate reconnaissance and security research. Do not ship functionality that encourages abuse. If you discover a vulnerability in oss-subfinder itself, please email the maintainers before disclosing publicly.

## Getting Help

Open a GitHub discussion or issue if you are unsure about design direction. Maintainers would rather steer early than request rework later.
