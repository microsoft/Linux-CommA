# Prototype of CommA Based on Elastic Stack #

A commit is just an event, right?

## Setup ##

```bash
apt install python3 python3-pip
pip3 install virtualenv virtualenvwrapper
mkvirtualenv comma
workon comma
setvirtualenvproject
pip install pygit2 elasticsearch flake8
```

### pygit2 ###

[pygit2 documentation](https://www.pygit2.org/index.html)

> Pygit2 is a set of Python bindings to the libgit2 shared library, libgit2
> implements the core of Git.

### elasticsearch-py ###

[elasticsearch-py documentation](https://elasticsearch-py.readthedocs.io/en/master/index.html)

> Official low-level client for Elasticsearch. Its goal is to provide common
> ground for all Elasticsearch-related code in Python; because of this it tries
> to be opinion-free and very extendable.

### flymake8 ###

[flymake8 documentation](https://pypi.org/project/flake8/)

> the modular source code checker: pep8, pyflakes and co
