class Console {
    constructor() {
        this.logBox = document.getElementById("log");
        this.vad = document.getElementById("vad");
        this.volume = document.getElementById("volume");
    }

    log(message) {
        let div = document.createElement("div");
        div.textContent = message;
        div.classList.add("log-line");
        this.logBox.append(div);
        this.logBox.scrollTop =  this.logBox.scrollHeight;
        
        if(this.logBox.children.length > 400) {
            this.logBox.removeChild(this.logBox.firstElementChild)
        }
    }

    log_control(message) {
        let div = document.createElement("div");
        div.textContent = message;
        div.classList.add("control-message");
        this.logBox.append(div);

        this.logBox.scrollTop =  this.logBox.scrollHeight;
    }

    update_vad(vad) {
        this.vad.innerText = vad;
    }

    update_volume(volume) {
        if (volume != null){
            this.volume.innerText = volume + "%";
        } else {
            this.volume.innerText = "?";
        }
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
        this.freeze = false;
    }

    onMessage(event) {
        let data = JSON.parse(event.data);
        if (data.type == "log") {
            this.log.log(data.log);
        } else if (data.type == "init") {
            this.initialize(data.data);
        } else if (data.type == "status") {
            this.log.update_vad(data.vad);
            this.log.update_volume(data.volume);
        } else {
            console.log("Unknown message: " + event.data);
        }
        return;
    }

    initialize(data) {
        this.freeze = true;
        let inputSelect = document.getElementById("input-device");
        let outputSelect = document.getElementById("output-device");
        while (inputSelect.firstChild) {
            inputSelect.remove(inputSelect.lastChild);
        }
        while (outputSelect.firstChild) {
            outputSelect.remove(outputSelect.lastChild);
        }

        let devices = []
        devices.push({'name': "None", 'id': null})
        for (var key in data.devices) {
            let device = data.devices[key];
            devices.push({'name': "Card " + device[1] + ": " + device[0], 'id': device[0]});
        }
        for (let i = 0; i < devices.length; i++) {
            let device = devices[i];
            let opt = document.createElement("option");
            opt.selected = data.speaker == device.id
            opt.value = device.id;
            opt.innerHTML = device.name;
            inputSelect.appendChild(opt);

            opt = document.createElement("option");
            opt.selected = data.microphone == device.id
            opt.value = device.id;
            opt.innerHTML = device.name;
            outputSelect.appendChild(opt);
        }
        let myself = this;
        document.getElementById("reset-button").onclick = function() { myself.reset()};
        document.getElementById("shutdown-button").onclick = function() { myself.shutdown()};
        document.getElementById("volume-up").onclick = function() { myself.volume_up()};
        document.getElementById("volume-down").onclick = function() { myself.volume_down()};
        inputSelect.onchange = function() { myself.set_microphone()};
        outputSelect.onchange = function() { myself.set_speaker()};
        for (let i = 0 ; i < data.log.length; i++) {
            this.log.log(data.log[i]);
        }
        this.freeze = false;
    }

    reset(){
        this.conn.send({'type': 'reset'})
    }

    shutdown(){
        this.conn.send({'type': 'shutdown'})
    }

    volume_up(){
        this.conn.send({'type': 'volume_up'})
    }

    volume_down(){
        this.conn.send({'type': 'volume_down'})
    }

    set_speaker(){
        if (!this.freeze) {
            let device = document.getElementById("output-device");
            this.conn.send({'type': 'set_speaker', 'speaker': device.selectedOptions[0].value})
        }
    }

    set_microphone(){
        if (!this.freeze) {
            let device = document.getElementById("input-device");
            this.conn.send({'type': 'set_microphone', 'speaker': device.selectedOptions[0].value})
        }
    }
}

window.addEventListener('load', (event) => {
    console.log('The page has fully loaded');
    new Main();
});