# Contributing

Thanks for your interest in Clara Desktop Installer.

## How to Contribute

1. **Open an issue** first to discuss the change you'd like to make (unless it's a trivial fix).
2. **Fork** the repository.
3. **Create a branch** with a descriptive name (`fix/disk-error-handling`, `feat/advanced-partitioning`).
4. **Make your changes** — keep `Code/main.py` as a single file.
5. **Add or update tests** in `Code/test_main.py`.
6. **Run the test suite**:

   ```cmd
   python -m pytest Code\test_main.py -v
   ```

7. **Submit a pull request** with a clear description of what you changed and why.

## Code Standards

- **Single-file design**: All installer logic stays in `Code/main.py`. Do not split into modules.
- **Windows-native**: Prefer PowerShell, cmd, and `subprocess` over third-party packages.
- **UEFI + BIOS**: Every feature must work on both firmware types unless explicitly documented.
- **No new dependencies**: The tool must run on a stock Windows 10/11 install.
- **Tests required**: Every function should have at least one passing and one failure test.

## Coding Style

- Python 3.10+ syntax
- `subprocess.run()` for all external commands
- f-strings, no `.format()` or `%`
- Guard clauses over nested `if`
- Descriptive function names, no abbreviations
- No comments unless the logic is non-obvious

## Commit Messages

Use conventional commits:

```
feat: add support for custom partition alignment
fix: handle missing bootsect.exe gracefully
docs: clarify system requirements in README
test: add tests for firmware detection fallback
```

## Review Process

Maintainers will review your PR within 5 business days. They may request changes before merging.
