# GitLab CI Integration

> **Coming Soon**: GitLab CI integration is planned for future releases.

## Overview

The lampe-sdk will support GitLab CI/CD for automated merge request description generation and code review. This integration will leverage GitLab's powerful CI/CD system and merge request API.

## Planned Features

- **Merge Request Analysis**: Generate descriptions for merge requests
- **Code Review Integration**: Automated review comments and suggestions
- **Pipeline Integration**: Seamless integration with GitLab CI/CD
- **Multiple Output Formats**: Support for GitLab's comment and note system

## Pipeline Configuration (Planned)

```yaml
# .gitlab-ci.yml
stages:
  - analysis

lampe-analysis:
  stage: analysis
  image: python:3.12
  before_script:
    - pip install git+https://github.com/montagne-dev/lampe.git@v0.1.0
  script:
    - lampe describe --output gitlab
  only:
    - merge_requests
  variables:
    OPENAI_API_KEY: $OPENAI_API_KEY
    ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY
```

## Environment Variables (Planned)

| Variable            | Description         | Required                    |
| ------------------- | ------------------- | --------------------------- |
| `OPENAI_API_KEY`    | OpenAI API key      | Yes                         |
| `ANTHROPIC_API_KEY` | Anthropic API key   | Yes (for agentic mode)      |
| `GITLAB_TOKEN`      | GitLab access token | Yes                         |
| `GITLAB_URL`        | GitLab instance URL | No (defaults to gitlab.com) |

## Commands (Planned)

- `lampe describe` - Generate merge request descriptions
- `lampe review` - Perform code review
- `lampe healthcheck` - Validate setup and configuration

## Output Providers (Planned)

- `gitlab` - Native GitLab merge request notes
- `console` - Console output for debugging
- `json` - Structured JSON output for custom processing

## Advanced Configuration (Planned)

### Custom Rules

```yaml
lampe-analysis:
  stage: analysis
  image: python:3.12
  script:
    - lampe describe --variant agentic --output gitlab
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      when: always
    - if: $CI_COMMIT_BRANCH == "main"
      when: never
```

### Multiple Jobs

```yaml
stages:
  - health-check
  - description
  - review

lampe-health:
  stage: health-check
  script:
    - lampe healthcheck

lampe-describe:
  stage: description
  script:
    - lampe describe --output gitlab
  dependencies:
    - lampe-health

lampe-review:
  stage: review
  script:
    - lampe review --variant agentic --output gitlab
  dependencies:
    - lampe-health
```

## GitLab Features Integration (Planned)

- **Merge Request Notes**: Automatic comments on merge requests
- **Pipeline Artifacts**: Generate and store analysis reports
- **Merge Request Templates**: Integration with GitLab's MR templates
- **Approval Rules**: Integration with GitLab's approval system

## Getting Notified

To be notified when GitLab integration is available:

1. Watch this repository for releases
2. Check the [GitHub Issues](https://github.com/montagne-dev/lampe/issues) for updates
3. Follow the project for announcements

## Contributing

If you're interested in helping with GitLab integration:

1. Check the [Contributing Guide](contributing.md)
2. Look for issues labeled "gitlab" or "ci"
3. Join discussions about the implementation approach

---

_This page will be updated as GitLab integration development progresses._
