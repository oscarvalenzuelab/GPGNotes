# Spell Checking

GPGNotes uses your preferred text editor (vim, nano, etc.) which already have spell checking built-in. No external dependencies needed!

## Vim / Neovim

### Enable Spell Check

```vim
:set spell spelllang=en_us    " Enable spell check
:set nospell                  " Disable spell check
```

### Navigation

| Command | Action |
|---------|--------|
| `]s` | Jump to next misspelled word |
| `[s` | Jump to previous misspelled word |
| `z=` | View suggestions for word under cursor |
| `zg` | Add word to dictionary |
| `zw` | Mark word as incorrect |

### Permanent Configuration

Add to `~/.vimrc`:

```vim
" Enable spell check for markdown files
autocmd FileType markdown setlocal spell spelllang=en_us

" Highlight misspelled words
hi SpellBad cterm=underline ctermfg=red
```

## Nano

### Start with Spell Check

```bash
nano -S filename.md
```

### Check Spelling While Editing

Press `Ctrl+T` to check spelling.

### Permanent Configuration

Add to `~/.nanorc`:

```bash
set speller "aspell -c"
```

## Emacs

### Enable Flyspell Mode

```elisp
M-x flyspell-mode
```

### Permanent Configuration

Add to `~/.emacs` or `~/.emacs.d/init.el`:

```elisp
;; Enable flyspell for text and markdown
(add-hook 'text-mode-hook 'flyspell-mode)
(add-hook 'markdown-mode-hook 'flyspell-mode)
```

## VS Code

If using VS Code as your editor (`notes config --editor "code --wait"`):

1. Install the "Code Spell Checker" extension
2. It automatically checks spelling in markdown files

## Tips

- GPGNotes opens vim/neovim with markdown syntax highlighting and spell check enabled by default
- The editor configuration includes proper text wrapping at 80 columns
- Use the [AI Enhancement](ai-enhancement.md) feature for grammar and style improvements beyond spell checking
