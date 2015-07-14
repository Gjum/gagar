agar for Python
===============

[![Join the chat at https://gitter.im/Gjum/pyAgar.io](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/Gjum/pyAgar.io?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

[agar.io](http://agar.io/) Python client with optional GTK frontend

    python3 main.py

Requires `pip install websocket-client` module for the headless client
and GTK for the optional GUI.

Under Arch Linux, you may also want to run

    pacman -S python-gobject python-cairo pygtk

to install the GTK dependencies. Other distros should have similar packages.

Controls
--------
| Key       | Action                |
|:----------|:----------------------|
| `R`       | respawn               |
| `Mouse`   | movement direction    |
| `W`       | shoot small cell      |
| `Space`   | split                 |
| `K`       | explode (disabled on official servers) |
| `C`       | reconnect to any server |
| `H`       | show/hide helpful cell info |
| `F3`      | show/hide FPS meter   |
| `Q`/`ESC` | quit                  |

Disclaimer
----------
This project isn't affiliated with [agar.io](http://agar.io/) in any way. When playing with this client, you do not get advertisements, which may be nice for you, but does not pay for the servers needed to run the game.

---

Licensed under GPLv3.
