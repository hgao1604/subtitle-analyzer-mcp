# Git Workflow Rules

## Commit Guidelines

### Commit Message Format

```
<type>: <subject>

<body>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring (no feature change)
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Rules

1. **Subject line**: Imperative mood, max 50 characters, no period
2. **Body**: Explain "why" not "what", wrap at 72 characters
3. **Co-author**: Always include Claude co-author line

### Examples

```bash
# Good
feat: add cookies file authentication support

# Bad
feat: Added cookies file authentication support.
```

## Branch Strategy

- `main`: Production-ready code
- `feat/*`: New features
- `fix/*`: Bug fixes

## Before Committing

1. Run syntax check: `python3 -m py_compile <files>`
2. Run tests if available: `pytest`
3. Review changes: `git diff`

## Push Rules

- Always push to feature branch first for large changes
- Direct push to `main` allowed for small fixes and docs
- Never force push to `main`
