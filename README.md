# RPi Intercom
A mumble client written in python that makes a raspberry pi run as an 'intercom'.  It can be used as a standalone service or imported as a library to integrate into other more complex projects.

## What does this do?
This lets you set up a raspberry pi as an intercom.  An intercom is a device that connects two points between to hear and be heard.  This projects sets up a Raspberry Pi to do that.  A Raspberry Pi intercom. It offers the following benefits:
 - Easy to set up
 - Configure GPIO inputs to mute/deafen/transmit/show connected status
 - Uses Mumble, so you can also connect to it from your phone/computer/whatever.
 - Requires no knowledge of Linux's truly arcane audio subystems


## What does this NOT do?
 - Solve problems that aren't related to intercoms.
 - Handle bad networks well.  There is no "anti-jitter" built into the audio processing like most audio clients so both sides of the intercom need to have a stable connection to the mumble server.
 - Handle echo cancellation.  This means that the audio played on a speaker "echos" back to the recipient unless the hardware you're using removes it.  The project _could_ eliminiate this in software but the algorithms for doing so are very hard. 

## Why does this exist?
I wanted to have an intercom between my living room and a basement office.  After researching products available on Amazon and projects that do something similar I couldn't find anything that was both secure and easy, so I made it instead.

## You will need
 - A Mumble server.  I host mine on a home server to keep everything local, but here isn't any reason it couldn't connect to the internet.
 - A raspberry pi.  
   - Worked well for me on the Rapsberry Pi 2, 3, and 4.  
   - Worked like crap on a Raspberry pi Zero (but what doesn't?).
   - Should theoretically work well on any Debian based environment.  No windows because of an ALSA dependency.
 - A speaker/microphone that does echo cancellation.  I bought this one on Amazon and it works great, but many ~$50 alternatives exist.  The echo cancellation is mandatory to avoid feedback that makes the intercom literally useless.  Don't try to skip on this.
 - Presumably you need a Raspberry Pi and speaker/microphone x2, so they can talk to eachother.

 ## Quick Start
 1. Install or acquire a mumble server.  you coudl even install it on one fo your raspberry pi's.
 2. Install the library:
    ```bash
    sudo python -m pip install rpi_intercom
    ```
    Note the ```sudo```.  This makes sure the library is installed for all users, which is important if you want to run it as a service later.
 3. Start the service on one or more devices:
    ```bash
    python -m rpi_intercom --server my-mumble-server.local
    ```
    
    ```--server``` is the only mandatory configuration, you will probably to specify more stuff.  With no further configuration it will use the default input and output sound device, connetct to the mumble server root, transmit constantly, and listen constantly.

## Install it as a service
I've written a convenience script to set up the device as a systemd service that starts at boot as a dedicated user and restarts automatically.  Once you have your configuration file, you can install the service a as by running:
```bash
sudo python -m rpi_intercom --install-service /path/to/your/config.yaml
```
Of course there is no reason you couldn't write the systemd unit file, create the user, etc yourself.


## Configuration
While everything can be passed in on the command line, this is very cumbersome.  Its better to create a configuration file, which you passin on the command line, eg:
```bash
python -m rpi_intercom --config /path/to/your/config.yaml
```

I even made a configuration script you can run to generate a config file easily by answering questions, which I recommend doing.  Try it out with:
```bash
python -m rpi_intercom --generate-config /path/to/put/the/config.yaml 
```

## More on configuration TBD