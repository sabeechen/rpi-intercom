class Console {
    constructor() {
        this.element = document.getElementById("log");
        this.vad = document.getElementById("vad");
    }

    log(message) {
        let div = document.createElement("div");
        div.textContent = message;
        div.classList.add("log-line");
        this.element.append(div);
        this.element.scrollTop =  this.element.scrollHeight;
    }

    log_control(message) {
        let div = document.createElement("div");
        div.textContent = message;
        div.classList.add("control-message");
        this.element.append(div);
        this.element.scrollTop =  this.element.scrollHeight;
    }

    update_vad(vad) {
        this.vad.innerText = vad;
    }
}

class Connection {
    constructor(handler, logger) {
        this.handler = handler;
        this.logger = logger;
        this.do_log_diconnect = true;
        this.reinitialize();
    }

    reinitialize() {
        this.socket = new WebSocket("ws://" + location.host + "/ws");
        let myself = this;

        this.socket.onclose = function(event) {
            myself.onClose(event);
        };
        this.socket.onerror = function(event) {
            myself.onError(event);
        };
        this.socket.onmessage = function(event) {
            myself.onMessage(event);
        };
    }
    
    onError(error) {
        console.log(`[error] ${error.message}`);
    };

    onClose(event) {
        if (event.wasClean) {
            console.log(`[close] Connection closed cleanly, code=${event.code} reason=${event.reason}`);
        } else {
            console.log('[close] Connection died');
        }
        if (this.do_log_diconnect) {
            this.logger.log_control("Disconnected from the server, attempting to reconnect...")
            this.do_log_diconnect = false;
        }
        this.reinitialize();
    };

    onMessage(event) {
        this.do_log_diconnect = true;
        this.handler.onMessage(event)
    };

    send(data) {
        this.socket.send(JSON.stringify(data));
    }
}

class Main {
    constructor() {
        this.url = "ws://" + location.host + "/ws";
        this.log = new Console();
        this.conn = new Connection(this, this.log);
    }

    onMessage(event) {
        let data = JSON.parse(event.data);
        if (data.type == "log") {
            this.log.log(data.log);
        } else if (data.type == "init") {
            this.initialize(data.data);
        } else if (data.type == "status") {
            this.log.update_vad(data.vad);
        } else {
            console.log("Unknown message: " + event.data);
        }
        return;
    }

    initialize(data) {
        let inputSelect = document.getElementById("input-device");
        let outputSelect = document.getElementById("output-device");
        while (inputSelect.firstChild) {
            inputSelect.remove(inputSelect.lastChild);
        }
        while (outputSelect.firstChild) {
            outputSelect.remove(outputSelect.lastChild);
        }
        for (var key in data.devices) {
            let device = data.devices[key];
            let opt = document.createElement("option");
            opt.value = device[1];
            opt.innerHTML = "Card " + device[1] + ": " + device[0];
            inputSelect.appendChild(opt);

            opt = document.createElement("option");
            opt.value = device[1];
            opt.innerHTML = "Card " + device[1] + ": " + device[0];
            outputSelect.appendChild(opt);
        }
        let myself = this;
        document.getElementById("reset-button").onclick = function() { myself.reset()};
        document.getElementById("shutdown-button").onclick = function() { myself.shutdown()};
    }

    reset(){
        this.conn.send({'type': 'reset'})
    }

    shutdown(){
        this.conn.send({'type': 'shutdown'})
    }
}

window.addEventListener('load', (event) => {
    console.log('The page has fully loaded');
    new Main();
});