# Contributing

The most useful contribution is a **report that an app or game will not run**: use the
"An app or game will not run" issue form. A missing library is usually a one-line fix that reaches
every installed system (see `docs/ROLLING-OUT-FIXES.md`).

To change code or packages:

```
python3 -m unittest discover -s tests       # must pass
python3 tools/validate-kiwi.py              # image description is sound
python3 tools/export-deps.py                # regenerate dist/normie-deps.list after editing package files
```

Adding a package? Read `docs/DEPENDENCY-POLICY.md` first (what is safe to add, what needs a decision),
and on a Fedora machine also run `tools/check-packages.py` and `tools/solve-check.py`.

By contributing you agree your work is licensed under GPL-3.0-or-later, like the rest of the project.
