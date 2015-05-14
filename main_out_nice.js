(function(window, jQuery) {
    function onLoad() {
        updateRegionList();
        setInterval(updateRegionList, 18E4);
        canvas = document.getElementById("canvas");
        drawcontext = canvas.getContext("2d");
        canvas.onmousedown = function(event) {
            if (isMobile) {
                var xx = event.clientX - (5 + windowWidth / 5 / 2);
                var yy = event.clientY - (5 + windowWidth / 5 / 2);
                if (Math.sqrt(xx * xx + yy * yy) <= windowWidth / 5 / 2) {
                    // tapped near the center
                    sendLargeMsg();
                    sendUint8(17);
                    return
                }
            }
            mouseX = event.clientX;
            mouseY = event.clientY;
            updMouse_();
            sendLargeMsg()
        };
        canvas.onmousemove = function(a) {
            mouseX = a.clientX;
            mouseY = a.clientY;
            updMouse_()
        };
        canvas.onmouseup = function(a) {};
        var a = false, b = false, c = false;
        window.onkeydown = function(e) {
            32 == e.keyCode && (sendLargeMsg(), sendUint8(17), a = true); // space
            87 == e.keyCode && (sendLargeMsg(), sendUint8(21), c = true); // W
            81 == e.keyCode && (sendUint8(18), b = true);                 // Q
            27 == e.keyCode && jQuery("#overlays").fadeIn(200);           // esc
        };
        window.onkeyup = function(e) {
            32 == e.keyCode && (a = false);
            87 == e.keyCode && (c = false);
            81 == e.keyCode && b && (sendUint8(19), b = false)
        };
        window.onblur = function() {
            sendUint8(19);
            c = b = a = false
        };
        window.onresize = ga;
        ga();
        window.requestAnimationFrame ? window.requestAnimationFrame(ha) : setInterval(redraw_, 1E3 / 60);
        setInterval(sendLargeMsg, 100);
        setRegion(jQuery("#region").val())
    }
    function doSomeMath() {
        if (.5 > speedDrag_)
            K = null;
        else {
            for (var a = Number.POSITIVE_INFINITY, b = Number.POSITIVE_INFINITY, c = Number.NEGATIVE_INFINITY, e = Number.NEGATIVE_INFINITY, d = 0, f = 0; f < p.length; f++)
                p[f].shouldRender() && (d = Math.max(p[f].size, d), a = Math.min(p[f].x, a), b = Math.min(p[f].y, b), c = Math.max(p[f].x, c), e = Math.max(p[f].y, e));
            K = QUAD.init({minX: a - (d + 100),minY: b - (d + 100),maxX: c + (d + 100),maxY: e + (d + 100)});
            for (f = 0; f < p.length; f++)
                if (a = p[f], a.shouldRender())
                    for (b = 0; b < a.points.length; ++b)
                        K.insert(a.points[b])
        }
    }
    function updMouse_() {
        mouseXRel_ = (mouseX - windowWidth / 2) / speedDrag_ + s;
        mouseYRel_ = (mouseY - windowHeight / 2) / speedDrag_ + t
    }
    function updateRegionList() {
        S == null && (
            S = {},
                jQuery("#region").children().each(function () {
                    var a = jQuery(this), b = a.val();
                    b && (S[b] = a.text())
                })
        );
        jQuery.get("http://m.agar.io/info", function(a) {
            for (var b in a.regions)
                jQuery('#region option[value="' + b + '"]').text(S[b] + " (" + a.regions[b].numPlayers + " players)")
        }, "json")
    }
    function hideOverlay() {
        jQuery("#adsBottom").hide();
        jQuery("#overlays").hide()
    }
    function setRegion(a) {
        a && a != $ && ($ = a, connect())
    }
    function connect() {
        jQuery("#connecting").show();
        connectServer();
        
        function connectServer() {
            jQuery.ajax("http://m.agar.io/", {
                error: function () {
                    setTimeout(connectServer, 1000)
                }, success: function (data) {
                    data = data.split("\n");
                    setupWebSock("ws://" + data[0])
                }, 
                dataType: "text", 
                method: "POST", 
                cache: false, 
                crossDomain: true, 
                data: $ || "?"
            })
        }
    }
    function setupWebSock(wsAddress) {
        webSock && (webSock.onopen = null, webSock.onmessage = null, webSock.onclose = null, webSock.close(), webSock = null);
        C = [];
        m = [];
        cellsById = {};
        p = [];
        D = [];
        leaderboard = [];
        console.log("Connecting to " + wsAddress);
        webSock = new WebSocket(wsAddress);
        webSock.binaryType = "arraybuffer";
        webSock.onopen = onSockOpen;
        webSock.onmessage = onSockRecv;
        webSock.onclose = onSockClose;
        webSock.onerror = function() {
            console.log("socket error")
        }
    }
    function onSockOpen(arrBuf) {
        jQuery("#connecting").hide();
        console.log("socket open");
        arrBuf = new ArrayBuffer(5);
        var dataView = new DataView(arrBuf);
        dataView.setUint8(0, 255);
        dataView.setUint32(1, 1, true);
        webSock.send(arrBuf);
        sendNick()
    }
    function onSockClose(a) {
        console.log("socket close");
        setTimeout(connect, 500)
    }
    function onSockRecv(recvFoo) {
        function getName() {
            for (var name = ""; ; ) {
                var b = recv.getUint16(bufPos, true);
                bufPos += 2;
                if (0 == b)
                    break;
                name += String.fromCharCode(b)
            }
            return name
        }
        var bufPos = 1, recv = new DataView(recvFoo.data);
        switch (recv.getUint8(0)) {
            case 16:
                updateTime_ = +new Date;
                var updateCode_ = Math.random(), c = 1;
                aa = false;
                // something is eaten?
                var num = recv.getUint16(c, true);
                c = c + 2;
                for (var i = 0; i < num; ++i) {
                    var ca = cellsById[recv.getUint32(c, true)],
                        cb = cellsById[recv.getUint32(c + 4, true)];
                    c += 8;
                    if (ca && cb) {
                        cb.destroy();
                        cb.ox = cb.x;
                        cb.oy = cb.y;
                        cb.oSize = cb.size;
                        cb.nx = ca.x;
                        cb.ny = ca.y;
                        cb.nSize = cb.size;
                        cb.updateTime = updateTime_;
                    }
                }
                for (; ;) {
                    var cellId = recv.getUint32(c, true);
                    c += 4;
                    if (0 == cellId)
                        break;
                    var cellX = recv.getFloat64(c, true);
                    c += 8;
                    var cellY = recv.getFloat64(c, true);
                    c += 8;
                    var cellSize = recv.getFloat64(c, true);
                    c += 8;

                    // read some kind of color hex?
                    recv.getUint8(c++);
                    var color_r = recv.getUint8(c++);
                    var color_g = recv.getUint8(c++);
                    var color_b = recv.getUint8(c++);
                    var someColor = (color_r << 16 | color_g << 8 | color_b).toString(16);
                    for (; 6 > someColor.length;)
                        someColor = "0" + someColor;
                    someColor = "#" + someColor;

                    var bitmask = recv.getUint8(c++);
                    var isVirus = !!(bitmask & 1);
                    bitmask & 2 && (c += 4);
                    bitmask & 4 && (c += 8);
                    bitmask & 8 && (c += 16);
                    for (var cellName = ""; ;) {
                        var someCell = recv.getUint16(c, true), c = c + 2;
                        if (0 == someCell)
                            break;
                        cellName += String.fromCharCode(someCell)
                    }
                    if (cellsById.hasOwnProperty(cellId)) {
                        someCell = cellsById[cellId];
                        someCell.updatePos();
                        someCell.ox = someCell.x;
                        someCell.oy = someCell.y;
                        someCell.oSize = someCell.size;
                        someCell.color = someColor;
                    } else {
                        someCell = new Cell_(cellId, cellX, cellY, cellSize, someColor, isVirus, cellName);
                        someCell.pX = cellX;
                        someCell.pY = cellY;
                    }
                    someCell.nx = cellX;
                    someCell.ny = cellY;
                    someCell.nSize = cellSize;
                    someCell.updateCode = updateCode_;
                    someCell.updateTime = updateTime_;
                    -1 != C.indexOf(cellId) && -1 == m.indexOf(someCell) && (document.getElementById("overlays").style.display = "none", m.push(someCell), 1 == m.length && (s = someCell.x, t = someCell.y))
                }
                recv.getUint16(c, true);
                c += 2;
                f = recv.getUint32(c, true);
                c += 4;
                for (d = 0; d < f; d++) {
                    cellId = recv.getUint32(c, true);
                    c += 4;
                    cellsById[cellId] && (cellsById[cellId].updateCode = updateCode_);
                }
                for (d = 0; d < p.length; d++)
                    p[d].updateCode != updateCode_ && p[d--].destroy();
                aa && 0 == m.length && jQuery("#overlays").fadeIn(3E3);
                break;
            case 17:
                x = recv.getFloat64(1, true);
                y = recv.getFloat64(9, true);
                speedMaybe_ = recv.getFloat64(17, true);
                break;
            case 20:
                m = [];
                C = [];
                break;
            case 32:
                C.push(recv.getUint32(1, true));
                break;
            case 49:
                var numFoos = recv.getUint32(bufPos, true);
                bufPos += 4;
                leaderboard = [];
                for (var d = 0; d < numFoos; ++d) {
                    var f = recv.getUint32(bufPos, true);
                    bufPos += 4;
                    leaderboard.push({id: f,name: getName()})
                }
                updateLeaderBoard();
                break;
            case 64:
                E = recv.getFloat64(1, true);
                F = recv.getFloat64(9, true);
                someXRecv_ = recv.getFloat64(17, true);
                someYRecv_ = recv.getFloat64(25, true);
                x = (someXRecv_ + E) / 2;
                y = (someYRecv_ + F) / 2;
                speedMaybe_ = 1;
                0 == m.length && (s = x, t = y, speedDrag_ = speedMaybe_)
        }
    }
    function sendLargeMsg() {
        if (null != webSock && webSock.readyState == webSock.OPEN) {
            var xx = mouseX - windowWidth / 2,
                yy = mouseY - windowHeight / 2;
            if (xx * xx + yy * yy >= 64) { // more than 8px moved
                if (oldMouseXRel_ != mouseXRel_ || oldMouseYRel_ != mouseYRel_) {
                    // mouse pos changed, notify server
                    oldMouseXRel_ = mouseXRel_;
                    oldMouseYRel_ = mouseYRel_;
                    var sendBuf = new ArrayBuffer(21);
                    var dataView = new DataView(sendBuf);
                    dataView.setUint8(0, 16);
                    dataView.setFloat64(1, mouseXRel_, true);
                    dataView.setFloat64(9, mouseYRel_, true);
                    dataView.setUint32(17, 0, true);
                    webSock.send(sendBuf);
                }
            }
        }
    }
    function sendNick() {
        if (null != webSock && webSock.readyState == webSock.OPEN && null != nickname) {
            var sendBuf = new ArrayBuffer(1 + 2 * nickname.length), b = new DataView(sendBuf);
            b.setUint8(0, 0);
            for (var c = 0; c < nickname.length; ++c)
                b.setUint16(1 + 2 * c, nickname.charCodeAt(c), true);
            webSock.send(sendBuf)
        }
    }
    function sendUint8(a) {
        if (null != webSock && webSock.readyState == webSock.OPEN) {
            var b = new ArrayBuffer(1);
            (new DataView(b)).setUint8(0, a);
            webSock.send(b)
        }
    }
    function ha() {
        redraw_();
        window.requestAnimationFrame(ha)
    }
    function ga() {
        windowWidth = window.innerWidth;
        windowHeight = window.innerHeight;
        canvas.width = canvas.width = windowWidth;
        canvas.height = canvas.height = windowHeight;
        redraw_()
    }
    function Aa() {
        if (m.length != 0) {
            for (var a = 0, b = 0; b < m.length; b++)
                a += m[b].size;
            a = Math.pow(Math.min(64 / a, 1), .4) * Math.max(windowHeight / 1080, windowWidth / 1920);
            speedDrag_ = (9 * speedDrag_ + a) / 10
        }
    }
    function redraw_() {
        var time = +new Date;
        ++Ba;
        updateTime_ = +new Date;
        if (m.length > 0) {
            Aa();
            var b = 0, c = 0;
            for (var i = 0; i < m.length; i++) {
                m[i].updatePos();
                b += m[i].x / m.length;
                c += m[i].y / m.length;
            }
            x = b;
            y = c;
            speedMaybe_ = speedDrag_;
            s = (s + b) / 2;
            t = (t + c) / 2
        }
        else {
            x > someXRecv_ - (windowWidth / 2 - 100) / speedDrag_ && (x = someXRecv_ - (windowWidth / 2 - 100) / speedDrag_);
            y > someYRecv_ - (windowHeight / 2 - 100) / speedDrag_ && (y = someYRecv_ - (windowHeight / 2 - 100) / speedDrag_);
            x < E + (windowWidth / 2 - 100) / speedDrag_ && (x = (E + windowWidth / 2 - 100) / speedDrag_);
            y < F + (windowHeight / 2 - 100) / speedDrag_ && (y = (F + windowHeight / 2 - 100) / speedDrag_);
            s = (29 * s + x) / 30;
            t = (29 * t + y) / 30;
            speedDrag_ = (9 * speedDrag_ + speedMaybe_) / 10;
        }
        doSomeMath();
        updMouse_();
        drawcontext.clearRect(0, 0, windowWidth, windowHeight);
        drawcontext.fillStyle = ba ? "#111111" : "#F2FBFF";
        drawcontext.fillRect(0, 0, windowWidth, windowHeight);
        drawcontext.save();
        drawcontext.strokeStyle = ba ? "#AAAAAA" : "#000000";
        drawcontext.globalAlpha = .2;
        drawcontext.scale(speedDrag_, speedDrag_);
        b = windowWidth / speedDrag_;
        c = windowHeight / speedDrag_;
        for (i = -.5 + (-s + b / 2) % 50; i < b; i += 50)
            drawcontext.beginPath(), drawcontext.moveTo(i, 0), drawcontext.lineTo(i, c), drawcontext.stroke();
        for (i = -.5 + (-t + c / 2) % 50; i < c; i += 50)
            drawcontext.beginPath(), drawcontext.moveTo(0, i), drawcontext.lineTo(b, i), drawcontext.stroke();
        drawcontext.restore();
        p.sort(function(a, b) {
            return a.size == b.size ? a.id - b.id : a.size - b.size
        });
        drawcontext.save();
        drawcontext.translate(windowWidth / 2, windowHeight / 2);
        drawcontext.scale(speedDrag_, speedDrag_);
        drawcontext.translate(-s, -t);
        for (i = 0; i < D.length; i++)
            D[i].draw();
        for (i = 0; i < p.length; i++)
            p[i].draw();
        drawcontext.restore();
        leaderBoardCanvas && 0 != leaderboard.length && drawcontext.drawImage(leaderBoardCanvas, windowWidth - leaderBoardCanvas.width - 10, 10);
        N = Math.max(N, Ca());
        0 != N && (null == T && (T = new NameCache_(24, "#FFFFFF")), T.setValue("Score: " + ~~(N / 100)), c = T.render(), b = c.width, drawcontext.globalAlpha = .2, drawcontext.fillStyle = "#000000", drawcontext.fillRect(10, windowHeight - 10 - 24 - 10, b + 10, 34), drawcontext.globalAlpha = 1, drawcontext.drawImage(c, 15, windowHeight - 10 - 24 - 5));
        Da();
        time = +new Date - time;
        time > 1E3 / 60 ? u -= .01 : time < 1E3 / 65 && (u += .01);
        .4 > u && (u = .4);
        1 < u && (u = 1)
    }
    function Da() {
        if (isMobile && ca.width) {
            var a = windowWidth / 5;
            drawcontext.drawImage(ca, 5, 5, a, a)
        }
    }
    function Ca() {
        for (var a = 0, b = 0; b < m.length; b++)
            a += m[b].nSize * m[b].nSize;
        return a
    }
    function updateLeaderBoard() {
        if (0 != leaderboard.length)
            if (V) {
                leaderBoardCanvas = document.createElement("canvas");
                var ctx = leaderBoardCanvas.getContext("2d"),
                    height_ = 60 + 24 * leaderboard.length,
                    c = Math.min(200, .3 * windowWidth) / 200;
                leaderBoardCanvas.width = 200 * c;
                leaderBoardCanvas.height = height_ * c;
                ctx.scale(c, c);
                ctx.globalAlpha = .4;
                ctx.fillStyle = "#000000";
                ctx.fillRect(0, 0, 200, height_);
                ctx.globalAlpha = 1;
                ctx.fillStyle = "#FFFFFF";
                c = null;
                c = "Leaderboard";
                ctx.font = "30px Ubuntu";
                ctx.fillText(c, 100 - ctx.measureText(c).width / 2, 40);
                ctx.font = "20px Ubuntu";
                for (var ypos = 0; ypos < leaderboard.length; ++ypos)
                    c = leaderboard[ypos].name || "An unnamed cell",
                    V || (c = "An unnamed cell"),
                        -1 != C.indexOf(leaderboard[ypos].id) ? (
                            m[0].name && (c = m[0].name),
                                ctx.fillStyle = "#FFAAAA"
                        ) : ctx.fillStyle = "#FFFFFF",
                        c = ypos + 1 + ". " + c,
                        ctx.fillText(c, 100 - ctx.measureText(c).width / 2, 70 + 24 * ypos)
            } else
                leaderBoardCanvas = null
    }
    function Cell_(id, x, y, size, color, isVirus, name) {
        p.push(this);
        cellsById[id] = this;
        this.id = id;
        this.ox = this.x = x;
        this.oy = this.y = y;
        this.oSize = this.size = size;
        this.color = color;
        this.isVirus = isVirus;
        this.points = [];
        this.pointsAcc = [];
        this.createPoints();
        this.setName(name);
    }
    function NameCache_(size, color, stroke, stroceColor) {
        size && (this._size = size);
        color && (this._color = color);
        this._stroke = !!stroke;
        stroceColor && (this._strokeColor = stroceColor)
    }
    if ("agar.io" != window.location.hostname && "localhost" != window.location.hostname && "10.10.2.13" != window.location.hostname)
        window.location = "http://agar.io/";
    else if (window.top != window)
        window.top.location = "http://agar.io/";
    else {
        var drawcontext, canvas, windowWidth, windowHeight, K = null,
            webSock = null,
            s = 0,
            t = 0,
            C = [],
            m = [],
            cellsById = {},
            p = [],
            D = [],
            leaderboard = [],
            mouseX = 0,
            mouseY = 0,
            mouseXRel_ = -1,
            mouseYRel_ = -1,
            Ba = 0,
            updateTime_ = 0,
            nickname = null,
            E = 0,
            F = 0,
            someXRecv_ = 1E4,
            someYRecv_ = 1E4,
            speedDrag_ = 1,
            $ = null,
            ra = true,
            V = true,
            da = false,
            aa = false,
            N = 0,
            ba = false,
            sa = false,
            x = s = ~~((E + someXRecv_) / 2),
            y = t = ~~((F + someYRecv_) / 2),
            speedMaybe_ = 1,
            isMobile = "ontouchstart" in window && /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent),
            ca = new Image;
        ca.src = "img/split.png";
        var S = null;
        window.setNick = function(newNickname) {
            hideOverlay();
            nickname = newNickname;
            sendNick();
            N = 0
        };
        window.setRegion = setRegion;
        window.setSkins = function(a) {
            ra =
            a
        };
        window.setNames = function(a) {
            V = a
        };
        window.setDarkTheme = function(a) {
            ba = a
        };
        window.setColors = function(a) {
            da = a
        };
        window.setShowMass = function(a) {
            sa = a
        };
        window.spectate = function() {
            sendUint8(1);
            hideOverlay()
        };
        window.connect = setupWebSock;
        var oldMouseXRel_ = -1,
            oldMouseYRel_ = -1,
            leaderBoardCanvas = null,
            u = 1,
            T = null,
            W = {},
            specialNames = "poland;usa;china;russia;canada;australia;spain;brazil;germany;ukraine;france;sweden;hitler;north korea;south korea;japan;united kingdom;earth;greece;latvia;lithuania;estonia;finland;norway;cia;maldivas;austria;nigeria;reddit;yaranaika;confederate;9gag;indiana;4chan;italy;ussr;bulgaria;tumblr;2ch.hk;hong kong;portugal;jamaica;german empire;mexico;sanik;switzerland;croatia;chile;indonesia;bangladesh;thailand;iran;iraq;peru;moon;botswana;bosnia;netherlands;european union;taiwan;pakistan;hungary;satanist;qing dynasty;nazi;matriarchy;patriarchy;feminism;ireland;texas;facepunch;prodota;cambodia;steam;piccolo;ea;india;kc;denmark;quebec;ayy lmao;sealand;bait;tsarist russia;origin;vinesauce;stalin;belgium;luxembourg;stussy;prussia;8ch;argentina;scotland;sir;romania;belarus;wojak;isis;doge;nasa;byzantium;imperial japan;french kingdom;somalia;turkey;mars;pokerface".split(";"),
            Fa = ["m'blob"];
        Cell_.prototype = {
            id: 0,
            points: null,
            pointsAcc: null,
            name: null,
            nameCache: null,
            sizeCache: null,
            x: 0,
            y: 0,
            size: 0,
            ox: 0,
            oy: 0,
            oSize: 0,
            nx: 0,
            ny: 0,
            nSize: 0,
            updateTime: 0,
            updateCode: 0,
            drawTime: 0,
            destroyed: false,
            isVirus: false,
            destroy: function () {
                var a;
                for (a = 0; a < p.length; a++)
                    if (p[a] == this) {
                        p.splice(a, 1);
                        break
                    }
                delete cellsById[this.id];
                a = m.indexOf(this);
                -1 != a && (aa = true, m.splice(a, 1));
                a = C.indexOf(this.id);
                -1 != a && C.splice(a, 1);
                this.destroyed = true;
                D.push(this)
            },
            getNameSize: function () {
                return Math.max(~~(.3 * this.size), 24)
            },
            setName: function (a) {
                if (this.name = a)
                    null == this.nameCache ? this.nameCache = new NameCache_(this.getNameSize(), "#FFFFFF", true, "#000000") : this.nameCache.setSize(this.getNameSize()), this.nameCache.setValue(this.name)
            },
            createPoints: function () {
                for (var a = this.getNumPoints(); this.points.length > a;) {
                    var b = ~~(Math.random() * this.points.length);
                    this.points.splice(b, 1);
                    this.pointsAcc.splice(b, 1)
                }
                0 == this.points.length && 0 < a && (this.points.push({
                    c: this,
                    v: this.size,
                    x: this.x,
                    y: this.y
                }), this.pointsAcc.push(Math.random() - .5));
                for (; this.points.length < a;) {
                    var b = ~~(Math.random() * this.points.length), c = this.points[b];
                    this.points.splice(b, 0, {c: this, v: c.v, x: c.x, y: c.y});
                    this.pointsAcc.splice(b, 0, this.pointsAcc[b])
                }
            },
            getNumPoints: function () {
                var a = 10;
                20 > this.size && (a = 5);
                this.isVirus && (a = 30);
                return ~~Math.max(this.size * speedDrag_ * (this.isVirus ? Math.min(2 * u, 1) : u), a)
            },
            movePoints: function () {
                this.createPoints();
                for (var a = this.points, b = this.pointsAcc, c = b.concat(), e = a.concat(), d = e.length, f = 0; f < d; ++f) {
                    var g = c[(f - 1 + d) % d], h = c[(f + 1) % d];
                    b[f] += Math.random() - .5;
                    b[f] *= .7;
                    10 < b[f] && (b[f] = 10);
                    -10 > b[f] && (b[f] = -10);
                    b[f] = (g + h + 8 * b[f]) / 10
                }
                for (var k = this, f = 0; f < d; ++f) {
                    c = e[f].v;
                    g = e[(f - 1 + d) % d].v;
                    h = e[(f + 1) % d].v;
                    if (15 < this.size && null != K) {
                        var l = false, n = a[f].x, m = a[f].y;
                        K.retrieve2(n - 5, m - 5, 10, 10, function (a) {
                            a.c != k && 25 > (n - a.x) * (n - a.x) + (m - a.y) * (m - a.y) && (l = true)
                        });
                        !l && (a[f].x < E || a[f].y < F || a[f].x > someXRecv_ || a[f].y > someYRecv_) && (l = true);
                        l && (0 < b[f] && (b[f] = 0), b[f] -= 1)
                    }
                    c += b[f];
                    0 > c && (c = 0);
                    c = (12 * c + this.size) / 13;
                    a[f].v = (g + h + 8 * c) / 10;
                    g = 2 * Math.PI / d;
                    h = this.points[f].v;
                    this.isVirus && 0 == f % 2 && (h += 5);
                    a[f].x = this.x + Math.cos(g * f) * h;
                    a[f].y = this.y + Math.sin(g * f) *
                        h
                }
            },
            updatePos: function () {
                var a;
                a = (updateTime_ - this.updateTime) / 120;
                a = 0 > a ? 0 : 1 < a ? 1 : a; // crop to 0..1
                a = a * a * (3 - 2 * a);
                this.getNameSize();
                if (this.destroyed && 1 <= a) {
                    var b = D.indexOf(this);
                    -1 != b && D.splice(b, 1)
                }
                this.x = a * (this.nx - this.ox) + this.ox;
                this.y = a * (this.ny - this.oy) + this.oy;
                this.size = a * (this.nSize - this.oSize) + this.oSize;
                return a
            },
            shouldRender: function () {
                return this.x + this.size + 40 < s - windowWidth / 2 / speedDrag_ || this.y + this.size + 40 < t - windowHeight / 2 / speedDrag_ || this.x - this.size - 40 > s + windowWidth / 2 / speedDrag_ || this.y - this.size - 40 > t + windowHeight / 2 / speedDrag_ ? false : true
            },
            draw: function () {
                if (this.shouldRender()) {
                    var a = !this.isVirus &&
                        .5 > speedDrag_;
                    drawcontext.save();
                    this.drawTime = updateTime_;
                    var b = this.updatePos();
                    this.destroyed && (drawcontext.globalAlpha *= 1 - b);
                    drawcontext.lineWidth = 10;
                    drawcontext.lineCap = "round";
                    drawcontext.lineJoin = this.isVirus ? "mitter" : "round";
                    da ? (drawcontext.fillStyle = "#FFFFFF", drawcontext.strokeStyle = "#AAAAAA") : (drawcontext.fillStyle = this.color, drawcontext.strokeStyle = this.color);
                    if (a)
                        drawcontext.beginPath(), drawcontext.arc(this.x, this.y, this.size, 0, 2 * Math.PI, false);
                    else {
                        this.movePoints();
                        drawcontext.beginPath();
                        b = this.getNumPoints();
                        drawcontext.moveTo(this.points[0].x, this.points[0].y);
                        for (var c = 1; c <= b; ++c) {
                            var e = c % b;
                            drawcontext.lineTo(this.points[e].x, this.points[e].y)
                        }
                    }
                    drawcontext.closePath();
                    b = this.name.toLowerCase();
                    ra ? -1 != specialNames.indexOf(b) ? (W.hasOwnProperty(b) || (W[b] = new Image, W[b].src = "skins/" + b + ".png"), c = W[b]) : c = null : c = null;
                    b = c ? -1 != Fa.indexOf(b) : false;
                    a || drawcontext.stroke();
                    drawcontext.fill();
                    null != c && 0 < c.width && !b && (drawcontext.save(), drawcontext.clip(), drawcontext.drawImage(c, this.x - this.size, this.y - this.size, 2 * this.size, 2 * this.size), drawcontext.restore());
                    (da || 15 < this.size) && !a && (drawcontext.strokeStyle = "#000000", drawcontext.globalAlpha *= .1, drawcontext.stroke());
                    drawcontext.globalAlpha = 1;
                    null != c && 0 < c.width && b && drawcontext.drawImage(c, this.x - 2 * this.size, this.y - 2 * this.size, 4 * this.size, 4 * this.size);
                    c = -1 != m.indexOf(this);
                    a = ~~this.y;
                    if ((V || c) && this.name && this.nameCache) {
                        e = this.nameCache;
                        e.setValue(this.name);
                        e.setSize(this.getNameSize());
                        b = Math.ceil(10 * speedDrag_) / 10;
                        e.setScale(b);
                        var e = e.render(), h = ~~(e.width / b), f = ~~(e.height / b);
                        drawcontext.drawImage(e, ~~this.x - ~~(h / 2), a - ~~(f / 2), h, f);
                        a += e.height / 2 / b + 4
                    }
                    sa && c && (null == this.sizeCache && (this.sizeCache = new NameCache_(this.getNameSize() / 2, "#FFFFFF", true, "#000000")), c = this.sizeCache, c.setSize(this.getNameSize() / 2), c.setValue(~~(this.size * this.size / 100)), b = Math.ceil(10 * speedDrag_) / 10, c.setScale(b),
                        e = c.render(), h = ~~(e.width / b), f = ~~(e.height / b), drawcontext.drawImage(e, ~~this.x - ~~(h / 2), a - ~~(f / 2), h, f));
                    drawcontext.restore()
                }
            }
        };
        NameCache_.prototype = {
            _value: "",
            _color: "#000000",
            _stroke: false,
            _strokeColor: "#000000",
            _size: 16,
            _canvas: null,
            _ctx: null,
            _dirty: false,
            _scale: 1,
            setSize: function (a) {
                this._size != a && (this._size = a, this._dirty = true)
            },
            setScale: function (a) {
                this._scale != a && (this._scale = a, this._dirty = true)
            },
            setColor: function (a) {
                this._color != a && (this._color = a, this._dirty = true)
            },
            setStroke: function (a) {
                this._stroke != a && (this._stroke = a, this._dirty = true)
            },
            setStrokeColor: function (a) {
                this._strokeColor != a && (this._strokeColor = a, this._dirty = true)
            },
            setValue: function (a) {
                a != this._value && (this._value = a, this._dirty = true)
            },
            render: function () {
                null == this._canvas && (this._canvas = document.createElement("canvas"), this._ctx = this._canvas.getContext("2d"));
                if (this._dirty) {
                    this._dirty = false;
                    var a = this._canvas, b = this._ctx, c = this._value, d = this._scale, g = this._size, f = g + "px Ubuntu";
                    b.font = f;
                    var h = b.measureText(c).width, k = ~~(.2 * g);
                    a.width = (h + 6) * d;
                    a.height = (g + k) * d;
                    b.font = f;
                    b.scale(d, d);
                    b.globalAlpha = 1;
                    b.lineWidth = 3;
                    b.strokeStyle = this._strokeColor;
                    b.fillStyle = this._color;
                    this._stroke && b.strokeText(c, 3, g - k / 2);
                    b.fillText(c, 3, g - k / 2)
                }
                return this._canvas
            }
        };
        window.onload = onLoad
    }
})(window, jQuery);
