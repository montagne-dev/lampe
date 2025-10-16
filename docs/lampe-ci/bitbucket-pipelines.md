# Bitbucket Pipelines Integration

> **Coming Soon**: Bitbucket Pipelines integration is planned for future releases.

## Overview

The lampe-sdk will support Bitbucket Pipelines for automated PR description generation and code review. This integration will provide similar functionality to GitHub Actions but optimized for Bitbucket's pipeline system.

## Planned Features

- **Automatic PR Analysis**: Generate descriptions for pull requests
- **Code Review Integration**: Automated code review comments
- **Health Checks**: Validate repository and configuration
- **Multiple Output Formats**: Support for Bitbucket's comment system

## Pipeline Configuration (Planned)

https://support.atlassian.com/bitbucket-cloud/docs/pipeline-start-conditions/#Pull-Requests

```yaml
# bitbucket-pipelines.yml
pipelines:
  pull-requests:
    "**":
      - step:
          name: Lampe Analysis
          image: python:3.12
          script:
            - pip install git+https://github.com/montagne-dev/lampe.git@v0.1.0
            - lampe describe --output bitbucket
          services:
            - docker
```

## Environment Variables (Planned)

| Variable                 | Description            | Required               |
| ------------------------ | ---------------------- | ---------------------- |
| `OPENAI_API_KEY`         | OpenAI API key         | Yes                    |
| `ANTHROPIC_API_KEY`      | Anthropic API key      | Yes (for agentic mode) |
| `BITBUCKET_APP_PASSWORD` | Bitbucket App Password | No                     |
| `BITBUCKET_USERNAME`     | Bitbucket Username     | No                     |

## Commands (Planned)

- `lampe describe` - Generate PR descriptions
- `lampe review` - Perform code review
- `lampe healthcheck` - Validate setup

## Output Providers (Planned)

- `bitbucket` - Native Bitbucket comments
- `console` - Console output for debugging
- `json` - Structured JSON output

## Getting Notified

To be notified when Bitbucket integration is available:

1. Watch this repository for releases
2. Check the [GitHub Issues](https://github.com/montagne-dev/lampe/issues) for updates
3. Follow the project for announcements

## Contributing

If you're interested in helping with Bitbucket integration:

1. Check the [Contributing Guide](contributing.md)
2. Look for issues labeled "bitbucket" or "pipelines"
3. Join discussions about the implementation approach

---

_This page will be updated as Bitbucket integration development progresses._
