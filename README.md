agar.io for Python
==================

[![Join the chat at https://gitter.im/Gjum/agario](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/Gjum/agario?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

Python client for the game [agar.io](http://agar.io/) with optional GTK frontend

Requires `pip install websocket-client` module for the headless client
and GTK for the optional GUI.

Under Arch Linux, you may also want to run

    pacman -S python-gobject python-cairo pygtk

to install the GTK dependencies. Other distros should have similar packages.

Run the GUI with

    python3 main.py -h

Controls
--------
| Key       | Action                |
|:----------|:----------------------|
| `S`       | spectate              |
| `R`       | respawn               |
| `Mouse`   | movement direction    |
| `W`       | shoot small cell      |
| `Space`   | split                 |
| `K`       | explode (disabled on official servers) |
| `C`       | reconnect to any server |
| `I`       | show/hide helpful cell info |
| `N`       | show/hide names       |
| `K`       | show/hide skins       |
| `M`       | show/hide movement lines |
| `G`       | show/hide grid        |
| `B`       | show/hide world border |
| `F1`      | show/hide overlays    |
| `F2`      | change background color |
| `F3`      | show/hide FPS meter   |
| `Q`/`ESC` | quit                  |

Disclaimer
----------
This project isn't affiliated with [agar.io](http://agar.io/) in any way. When playing with this client, you do not get advertisements, which may be nice for you, but does not pay for the servers needed to run the game.

---

Licensed under GPLv3.
