# GitHub Pages Setup for Documentation

This document explains how to configure GitHub Pages to automatically deploy the MkDocs documentation for this project.

## Prerequisites

1. The repository must be public or you must have GitHub Pro/Team/Enterprise
2. You must have admin access to the repository

## Configuration Steps

### 1. Enable GitHub Pages

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Pages**
3. Under **Source**, select **GitHub Actions**
4. Save the configuration

### 2. Repository Settings

The workflow is configured to:
- Build the MkDocs site on every push to `main` branch
- Deploy to GitHub Pages automatically
- Use the `github-pages` environment for deployment

### 3. Workflow Details

The workflow (`.github/workflows/docs.yml`) includes:

- **Build Job**:
  - Installs dependencies using `uv`
  - Builds the MkDocs site using `mkdocs build`
  - Uploads the built site as an artifact

- **Deploy Job**:
  - Only runs on `main` branch pushes
  - Deploys the built site to GitHub Pages
  - Uses the official GitHub Pages deployment action

### 4. Environment Configuration

The workflow uses the `github-pages` environment. If you need to configure additional settings:

1. Go to **Settings** → **Environments**
2. Create or configure the `github-pages` environment
3. Add any required secrets or variables

### 5. Accessing the Documentation

Once deployed, your documentation will be available at:
```
https://<username>.github.io/<repository-name>
```

For this repository, it will be:
```
https://montagne-dev.github.io/lampe
```

## Local Development

To build the documentation locally:

```bash
# Install dependencies
uv sync --locked --all-extras --dev

# Build the site
uv run mkdocs build

# Serve locally for preview
uv run mkdocs serve
```

## Troubleshooting

### Common Issues

1. **Build Failures**: Check the Actions tab for detailed error logs
2. **Permission Issues**: Ensure the repository has Pages enabled and the workflow has proper permissions
3. **Environment Issues**: Verify the `github-pages` environment exists and is properly configured

### Manual Deployment

If automatic deployment fails, you can manually trigger the workflow:

1. Go to **Actions** tab
2. Select the "Deploy Documentation" workflow
3. Click "Run workflow"
4. Select the branch and click "Run workflow"

## Customization

To customize the documentation build:

1. Modify `mkdocs.yml` for MkDocs configuration
2. Update the workflow in `.github/workflows/docs.yml` for build process changes
3. Add additional build steps or dependencies as needed

## Security

The workflow uses:
- `contents: read` - to read repository contents
- `pages: write` - to deploy to GitHub Pages
- `id-token: write` - for OIDC token generation

These are the minimal permissions required for GitHub Pages deployment.
