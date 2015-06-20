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
from creator import *

GamelogCreator().create()
```
