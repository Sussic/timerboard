# aa-timerpaste-standalone

Fully standalone Alliance Auth plugin for bulk pasting messy EVE timer text.

## Key point

This plugin does **not** require editing the existing Alliance Auth Structure Timers module.
It is a separate AA app with its own:

- models
- URLs
- views
- templates
- menu entry
- permissions
- SDE import command

The only host-level change should be the normal plugin installation step:
- add the app to `INSTALLED_APPS`
- run migrations
- collect static
- import SDE data
- assign permissions

## What it does

- accepts pasted Discord / clipboard timer dumps
- parses common EVE timer formats
- enriches systems with regions from local SDE data
- shows a preview
- saves parsed timers into its **own database tables**
- exposes its **own list page**

## What it does not do

- does not patch the existing timerboard
- does not import into the existing timerboard tables
- does not require modifying old forms, old views, or old models
- does not depend on old timerboard internals

## Install

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS += [
    "aa_timerpaste",
]
```

Then run:

```bash
python manage.py makemigrations aa_timerpaste
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py import_timerpaste_sde /path/to/sde/fsd/universe/eve
```

## Pages

- `/timerpaste/` - list page
- `/timerpaste/paste/` - paste + preview + save

## App boundaries

This module is intentionally isolated. It should be reviewable like any other AA plugin.
A maintainer can install or remove it without changing the existing timerboard module.

## Handoff summary

Tell the maintainer:

> This is a standalone Alliance Auth plugin. Install it like a normal plugin. It does not replace or edit the existing timerboard app.

## v2 changes

- Objective defaults to Hostile.
- Preview rows are editable before save.
- Preview rows can be removed with a checkbox.
- Distance is ignored and not stored.
- Timer list page has client-side search and sortable columns.
- Parsed status column removed from main board.


## Packaging notes

This version includes packaging metadata for `pip install git+...` installs:

- `include-package-data = true`
- `MANIFEST.in` for Django templates, migrations, and static files

That is intended to prevent reinstall issues where templates are missing from the installed package.
