# Version Control Guidelines

This document provides information about which files are tracked in version control and which ones are ignored.

## Tracked Files

- Core Python scripts and modules for LOC analysis
- HTML templates and static file directories (with placeholder .gitkeep files)
- Documentation files (README.md, etc.)
- Configuration files (requirements.txt, etc.)

## Ignored Files

### Environment and System Files
- Python virtual environment directories (venv/, env/)
- Python bytecode files (__pycache__/, *.pyc, etc.)
- OS-specific files (.DS_Store, etc.)
- Editor/IDE files (.vscode/, .idea/, etc.)

### Generated Data and Output Files
- Generated CSV files (*_loc.csv, *_stats.csv, etc.)
- Generated image files (*_changes.png, *_stats.png, etc.)
- Temporary data files in static/data/ and static/images/
- Analysis reports and JSON data files

### Security-Sensitive Files
- Authentication token files (*.token, *.key)
- Credential files (credentials.json, token.txt)
- Environment setup scripts with tokens or passwords

### Environment-Specific Shell Scripts
- Authentication and token-related scripts
- Environment setup scripts
- Repository-specific test scripts

## Managing Ignored Files

If you need to track files that are normally ignored, you can use:
```bash
git add -f <filename>
```

To check which files would be ignored, use:
```bash
git status --ignored
```
