# Cross-platform Packaging

Use Python packaging to produce source and wheel artifacts that can be installed on macOS, Windows, and Linux.

## Build
```bash
.venv/bin/pip install build
.venv/bin/python -m build
```

Artifacts are written to `dist/`.

## Verify install
```bash
python -m pip install dist/dnd_vtt-0.1.0-py3-none-any.whl
python -c "from desktop.app.main import main; main()"
```

## Platform notes
- macOS/Windows/Linux can consume the same wheel because this MVP is pure Python.
- Native desktop UI packaging can be added later with PyInstaller/Briefcase.
