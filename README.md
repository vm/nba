## some rough installation instructions

before setting up, make sure you have virtualenv and mongo installed -- if you're
using virtualenvwrapper or something else, these instructions won't be as helpful.

provided you have virtualenv and pip, you shouldn't ever need to sudo.

installation instructions for mongo: http://docs.mongodb.org/manual/tutorial/getting-started/

```sh
cd $HOME/projects (or wherever you keep your projects)
```

```sh
git clone https://github.com/vigneshmohankumar/statcruncher.git && virtualenv statcruncher
```

```sh
cd statcruncher && source bin/activate
```

you should be set up in a virtualenv now -- verify this by running:

```sh
which python
```

it should output something like:

```sh
/Users/arjun/projects/statcruncher/bin/python
```

install all dependencies:

```sh
pip install -r requirements.txt
```