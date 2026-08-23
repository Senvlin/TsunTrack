# TsunTrack

<div align="center">

🌏 Language: [简体中文](README.zh.md) | **English**

</div>

> Make Python errors **tsundere**～

---

A global exception beautifier built on [rich](https://github.com/Textualize/rich) — zero-intrusion, purely configuration-driven, install-and-go, and shipped with a built-in tsundere personality.

## Screenshots

Without installation / when disabled:

<img width="907" height="211" alt="zzz" src="https://github.com/user-attachments/assets/7307dcf1-858f-4541-b502-b852a5badb9d" />

After installation and enabling:

<img width="909" height="271" alt="image" src="https://github.com/user-attachments/assets/4acd8f2b-bb24-4956-8b19-a83dca7c8acd" />

## Features

- **Theme switching**: errors are no longer cold, bare stack traces. Change one line — `[general] theme = "..."` — and freely switch to any style: sarcastic, healing, chuunibyou… whatever you like
- **Install & go**: hooks are installed automatically at interpreter startup via `tsuntrack_auto.pth`; zero changes to your business code
- **Configuration-driven**: all error messages and styles come from a TOML config; colors are customizable, with support for partial overrides and extended placeholders
- **Manual API**: you can also enable it manually with `import tsuntrack; tsuntrack.install()`
- **Smart hint enhancement**: keeps and beautifies Python's native `did-you-mean` suggestions
- **Rich text**: stack traces come with syntax highlighting and multiple themes; the config supports Rich markup such as `[green]` / `[red]`
- **Coroutine & thread support**

> Just want the error beautification? Set the `theme` field to an empty string and give it a try.

## Installation

Requires Python 3.11+. Install with pip:

```powershell
pip install tsuntrack
```

No import needed after installation — just run any script that raises an error and see the result:

```powershell
python -c "print(1/0)"
```

## Manual Enable / Disable

```python
import tsuntrack

tsuntrack.install()  # Enable
tsuntrack.uninstall()  # Disable, restoring default behavior
```

## Configuration

### Lookup order (highest priority first)

1. The path specified by the `TSUNTRACK_CONFIG` environment variable
2. `tsuntrack.toml` in the current working directory
3. `~/.config/tsuntrack/config.toml` in the user's home directory
4. The bundled `defaults.toml` inside the package

User configuration and defaults are **deep-merged** — just write the fields you want to change.

### Built-in Themes & Languages

Five themes are built in; switch with `[general] theme`:

| Theme | Style | Description |
| --- | --- | --- |
| `tsundere` | Tsundere | Default theme; tough on the outside, soft inside |
| `neko` | Catgirl | Calls you master and serves you dutifully |
| `sarcastic` | Sharp-tongued | Biting sarcasm, but always tells the truth |
| `yandere` | Yandere | Sweet on the surface, dangerously possessive |
| `chuunibyou` | Chuunibyou | Every error comes with an anime trope |

Two languages are built in; switch with `[general] language` (default `en`): `zh` (Simplified Chinese) / `en` (English)
> Want to contribute a new language or a new theme? copy `locales/en.toml`, translate it, save it as `locales/xx.toml`, and set `language = "xx"`.

### Example

```toml
[general]
enabled = true # Master switch
theme = "tsundere" # Current theme
language = "zh" # Language: zh / en
max_frames = 5 # Max stack frames shown (keeps the innermost ones)
context_lines = 1 # Lines of context code to show
error_line_style = "bold red" # Highlight color for the error line
line_number_style = "dim" # Line-number color
show_hints = true # Whether to show hints

# Context code highlighting:

[general.syntax]
# - theme: a built-in Pygments theme name (e.g. monokai / default / emacs / friendly / tango)
theme = "monokai"

[general.syntax.styles]
# - styles: Pygments token name → Rich style. Token names such as Keyword / Name.Function / String.Doc.
# Keys must be real Pygments tokens; made-up ones are hidden by default.
"Comment.Special" = "bold #5C6370"
"Comment" = "#5C6370"
"String.Doc" = "italic #5C6370"
"String" = "#98C379"
...

# Override the message for a specific exception inside a theme
[theme."tsundere".exceptions.NameError]
template = 'You dummy! I-I would never tell you that "{name}" is not defined. Hmph ╯^╰'
```

### Themes

The configuration merges in three layers, **highest priority first**:

1. **User config** (`tsuntrack.toml` / file specified by the env var / `~/.config/...`) — directly overrides anything below
2. **Theme override layer** (`[theme."theme-name".*]`) — overrides the base config according to the theme selected by `[general] theme`
3. **Base config** (the parts of `defaults.toml` other than `[theme.*]`) — shared by all themes, with `exceptions.default` as the fallback

```toml
# 1) Switch built-in themes
[general]
theme = "tsundere"

# 2) Override any config directly
[exceptions.NameError]
template = 'My custom message: {name}'

# 3) Custom themes (just add a [theme."name"...] section to your own config)
[general]
theme = "我的主题"

[theme."我的主题".exceptions.NameError]
template = 'My theme message: {name}'
```

### Placeholders

| Placeholder | Meaning | Example |
| --- | --- | --- |
| `{name}` | Variable / attribute / module / key name (NameError, AttributeError, ModuleNotFoundError, KeyError, etc.) | `some_undefined_name` |
| `{message}` | The exception's own message text | `division by zero` |
| `{exc_type}` | Exception type name | `NameError` |
| `{filename}` | Path of the file where the error occurred (innermost stack frame) | `C:\demo\app.py` |
| `{lineno}` | Line number of the error | `8` |
| `{func_name}` | Name of the function where the error occurred | `level_1` |
| `{module}` | Name of the module where the error occurred | `app` |

#### Custom placeholders (`[extra]`)

You can add an `[extra]` section to your user config or a theme to define arbitrary extra placeholders:

```toml
# tsuntrack.toml (or the config specified by the environment variable)
[extra]
service = "order-api"
env = "production"
```

```toml
[theme."neko".exceptions.default]
template = 'Master, {service} failed in the {env} environment ┭┮﹏┭┮: {message}. Leave it to me!'
```

Output: `Master, order-api failed in production ┭┮﹏┭┮: ...`

- Keys in `[extra]` override built-in fields when they share a name with one in `[general]`
- The theme layer works the same way: `[theme."X".extra]` lets you define different placeholders per theme
- You can also call it from code: `formatter.format_message(exc_type, exc_value, tb, cfg, extra={"service": "x"})`

### Disabling

```toml
[general]
enabled = false
```

Put this in a config file at any priority level to disable globally (the hooks will not be installed).

## Known Limitations

- `sys.unraisablehook` is not handled yet
- `asyncio` intrudes into the global policy; for `uvloop` we can only wrap it for now
  > If another library also replaces `sys.excepthook`, it may silently override this one
- In modes such as `python -S` (which doesn't load `site`), `.pth` files are not executed, so you need to call `tsuntrack.install()` manually

## License

MIT
