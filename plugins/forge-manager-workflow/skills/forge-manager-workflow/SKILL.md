---
name: forge-manager-workflow
description: Run forge-manager-workflow from the installed public package CLI.
---

# forge-manager-workflow

This public workflow skill is for a fresh public repository install.

Install the package first:

```bash
python -m pip install git+https://github.com/YaofeiHe/forge-manager-public.git
```

Use the installed CLI or module entrypoint; do not call a private local checkout path.

```bash
forge-manager --help
```

Do not read local credentials, private runtime directories, `.env`, tokens, cookies, browser profiles, or host-specific paths.
