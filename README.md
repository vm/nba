## NBA API for Player, Gamelog, Head-to-head data.

### Installation
Clone the repo.
```shell
git clone https://github.com/vm/nba.git
```

Install python requirements.
```shell
pip install -r requirements.txt
```

Create all the data.
```python
from api import create

create('players')  # Must create players first.
create('gamelogs')
create('headtoheads')  # This will never finish, for now. Working on it.
```

To use the data, open `mongo` shell.
```mongo
use nba;
db.gamelogs.find({ 'Pts': 81 });
```
