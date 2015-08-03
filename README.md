gagar
=====

[![Join the chat at https://gitter.im/Gjum/gagar](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/Gjum/gagar?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

Standalone graphical [agar.io](http://agar.io/) Python client using GTK

![Screenshot of gagar](http://lunarco.de/gagar/img/2015-08-01-151935_1000x562_scrot.png)

Features
--------
- mass graph
- minimap
- skins
- show eatability/hostility level of other cells
- force fields for eatable/hostile cells
- show/hide anything via key bindings
- extend with your own plugins (more stats, server chooser, bot, ...)

###Roadmap
- command-line arguments (nick, gamemode, facebook token)
- better virus interaction
- zoom
- make it work with Ogar
- documentation
- config file

Installation
------------
First install agarnet:

    pip install agarnet

Under Arch Linux, you then want to run

    pacman -S python-gobject python-cairo pygtk

to install the GTK dependencies. Other distros should have similar packages.

Someone also got it to work on Mac using MacPorts.

Run the GUI with

    python3 main.py -h

Controls
--------
| Key       | Action                |
|:----------|:----------------------|
| `S`       | spectate              |
| `R`/`RETURN` | respawn            |
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

About
-----
This is a hobby project of me, on which I work in my free time.

Pull requests are more than welcome, but you should open an issue first, so we can talk about it.

I reverse-engineered the protocol implementation by looking at the (barely) obfuscated Javascript code on the agar.io website.
Although it would be much easier now to write a client, because [there is a wiki](http://agar.gcommer.com/) describing the whole protocol and most game mechanics.

If you have any game-related questions, feel free to ask in the [#agariomods IRC channel on the Rizon network](http://irc.lc/rizon/agariomods/CodeBlob@@@).
For questions about this client specifically, [open an issue](https://github.com/Gjum/gagar/issues/new) or write me an email: [code.gjum@gmail.com](mailto:code.gjum@gmail.com)

Disclaimer
----------
This project isn't affiliated with [agar.io](http://agar.io/) in any way. When playing with this client, you do not get advertisements, which may be nice for you, but does not pay for the servers needed to run the game.

---

Licensed under GPLv3.
