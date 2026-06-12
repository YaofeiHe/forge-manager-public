# forge-manager

<!-- nexus:public-install -->
## Public Install

Install the public package from GitHub:

```bash
python -m pip install git+https://github.com/YaofeiHe/forge-manager-public.git
```

Smoke test the installed command:

```bash
forge-manager --help
```

Codex workflow/skill install:

```bash
tmp="$(mktemp -d)" && git clone --depth 1 https://github.com/YaofeiHe/forge-manager-public.git "$tmp/repo" && mkdir -p "$HOME/.agents/skills" && for skill in .github/skills/forge-manager-workflow skills/forge-manager-workflow; do cp -R "$tmp/repo/$skill" "$HOME/.agents/skills/"; done
```

This installs the workflow skill directly from the repository files into `$HOME/.agents/skills`.

Private runtime files, credentials, `.env`, tokens, cookies, browser profiles, `.data/`, `.nexus/private/`, and local host paths are not part of the public release.
