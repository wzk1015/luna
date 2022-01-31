# Luna: simple version control system

wzk's little project for entertainment, don't take it seriously~



## Introduction

"luna" can mean anything, depending on your mood.

 - the goddess of the moon in Roman mythology: isn't it great?
 - `"light unix-like navigating assistant"`: you're in a good mood, and it actually
   works for you. Angels sing, and a light suddenly fills the room. 
 - `"loony unsteady nerd a****le"`: when it breaks
 - Luna Lovegood in *HP*: correct!

> Following the introduction of [Git](https://github.com/git/git), hahaha



## Usage

### installation

`python setup.py develop `

then reopen your shell.

### Use in shell (command line)  -- **recommended**

Note: support Linux and Mac OS   (try git bash if using Windows)

```shell script
mkdir test
cd test
luna init
touch 666.txt
luna commit "first commit"
touch hahaha
echo "hello world" >> 666.txt
luna diff
luna commit "second commit"
luna log
luna diff 1 2
luna diff 1 666.txt
luna reset 1
luna reset 2
luna history
luna delete 1
luna info
luna discard
```



### Use in python

```python
from luna import *
p = "/SOME/PATH"
init(p)
makefile(p, "1")
commit(p, "commit 1")
makefile(p, "2")
commit(p, "commit 2")
revise(p, 2, "commit 3 new message")
reset(p, 1)
reset(p, 2)
history(p)
```

