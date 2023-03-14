---
title: Pyblish ReadMe
authors:
- name: Loïc Rouquette
use: \_journals/iacrtrans.yml
---

[This is a convertion of ReadMe.ipynb](ReadMe.ipynb)

# Pyblish

Pyblish is a python application that convert Jupyter notebooks (`ipynb`)
into journal publications. It runs [Pandoc](https://pandoc.org/) under
the hood, applies some default extensions and provides some basic
filters.

## Builtins

Pyblish has some HTML and Latex extensions. It’s allows to write plain
python code and produce Latex and HTML ready to publish code.

For exemple Pyblish provides the `Figure` class which allows to create a
Figure environment.

Usage:

``` python
from pyblish import Figure
Figure("""This is markdown **here**!""")
```

<div class="output execute_result" execution_count="2">

    <figure>This is markdown <b>here</b>!<figure>

</div>

This code will produce the HTML code:

``` html
<figure>This is markdown <b>here</b>!<figure>
```

to render the content in the jupyter environment and:

``` latex
\begin{figure}
This is markdown \textbf{here}!
\end{figure}
```

to render in the Latex code source.

## Journals

The provided journals are stored in the [\_journals](_journals)
directory.

### IACRTrans

The iarctrans journal can be used to publish in both
[ToSC](https://tosc.iacr.org/index.php/ToSC/index) and
[TCHES](https://tches.iacr.org/)

To use this journal add:

``` yml
use: _journal/iacrtrans.yml
```

to your yml metadata file.
