# Prototype of CommA Based on Elastic Stack #

A commit is just an event, right?

## Setup ##

```bash
apt install python3 python3-pip
pip3 install virtualenv virtualenvwrapper
mkvirtualenv comma
workon comma
setvirtualenvproject
pip install pygit2 elasticsearch-dsl
```

### pygit2 ###

[pygit2 documentation](https://www.pygit2.org/index.html)

> Pygit2 is a set of Python bindings to the libgit2 shared library, libgit2
> implements the core of Git.

### elasticsearch-dsl ###

[elasticsearch-dsl documentation](https://elasticsearch-dsl.readthedocs.io/en/latest/index.html)

> It also provides an optional persistence layer for working with documents as
> Python objects in an ORM-like fashion: defining mappings, retrieving and
> saving documents, wrapping the document data in user-defined classes.
