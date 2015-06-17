## NBA API for Player, Gamelog, Head-to-head data.

### Installation
Clone the repo.
```shell
git clone https://github.com/vm/nba-api.git
```

Install python requirements.
```shell
pip install -r requirements.txt
```

Create all the data.
```python
from ingest import *

CollectionCreator('players').create()
CollectionCreator('gamelogs', update=False).create()

# The combinations algorithm needs work, but this runs.
CollectionCreator('headtoheads').create()
```
