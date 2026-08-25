# assets/paper — shared LaTeX machinery

`preamble.tex` only: packages, colours, box styles, macros. It is frame-independent — nothing here knows what any lab is about.

**What deliberately does not live here:** a lab's `references.bib` and its `figures/`. Those are the lab's content, they change when its findings change, and a figure is only ever meaningful next to the results it draws. Each lab keeps them under its own `assets/paper/`.

Built PDFs are derived bytes and are never tracked. Regenerate figures from their SVG sources and generators.
