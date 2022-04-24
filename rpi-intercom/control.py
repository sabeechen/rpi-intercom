from typing import List
from .config import Config, PinConfig
from gpiozero import Button, LED, GPIODevice

DEBOUNCE_SECONDS = None

class Control:
    '''
    Allows control over the intercom using properties.
    '''
    def __init__(self, config: Config):
        self._config = config
        self._buttons: List[GPIODevice] = []
        self._transmitting = True
        self._deafened = False
        self._muted = False
        self._connected = False
        self._recieving = False

        self._transmitting_controls: List[LED] = []
        self._muted_controls: List[LED] = []
        self._deafened_controls: List[LED] = []
        self._connected_controls: List[LED] = []
        self._recieving_controls: List[LED] = []

    def start(self):
        '''
        Starts listening for events on configured GPIO pins and using
        them control the intercom.
        '''
        assigments = self._config.pins
        for pin in assigments:
            value = assigments[pin]
            if value == PinConfig.ACTION_HOLD_TO_TRANSMIT.value:
                button = Button(pin, bounce_time=DEBOUNCE_SECONDS)
                button.when_activated = lambda: self.__set_transmitting(True)
                button.when_deactivated = lambda: self.__set_transmitting(False)
                self._buttons.append(button)
                self._transmitting = button.is_active
            elif value == PinConfig.ACTION_TOOGLE_TRANSMIT.value:
                button = Button(pin, bounce_time=DEBOUNCE_SECONDS)
                button.when_activated = lambda: self.__set_transmitting(not self.transmitting)
                self._buttons.append(button)
                self._transmitting = button.is_active
            elif value == PinConfig.ACTION_HOLD_TO_DEAFEN.value:
                button = Button(pin, bounce_time=DEBOUNCE_SECONDS)
                button.when_activated = lambda: self.__set_deafened(True)
                button.when_deactivated = lambda: self.__set_deafened(False)
                self._buttons.append(button)
                self._deafened = button.is_active
            elif value == PinConfig.ACTION_TOOGLE_DEAFEN.value:
                button = Button(pin, bounce_time=DEBOUNCE_SECONDS)
                button.when_activated = lambda: self.__set_deafened(not self.deafened)
                self._buttons.append(button)
                self._deafened = button.is_active

            elif value == PinConfig.STATUS_TRANSMITTING.value:
                self._transmitting_controls.append(LED(pin))
            elif value == PinConfig.STATUS_CONNECTED.value:
                self._connected_controls.append(LED(pin))
            elif value == PinConfig.STATUS_DEAFENED.value:
                self._deafened_controls.append(LED(pin))
            elif value == PinConfig.STATUS_RECIEVING.value:
                self._recieving_controls.append(LED(pin))

        for led in self._transmitting_controls:
            if self._transmitting:
                led.on()
            else:
                led.off()

        for led in self._connected_controls:
            led.off()


        for led in self._deafened_controls:
            if self._deafened:
                led.on()
            else:
                led.off()

        for led in self._recieving_controls:
            led.off()

    def __set_deafened(self, value):
        self.deafened = value

    def __set_transmitting(self, value):
        self.transmitting = value

    def stop(self):
        '''
        Stops listening on GPIO pins for evetns.
        '''
        for button in self._buttons:
            button.close()
        for led in self._connected_controls:
            led.off()
            led.close()
        for led in self._transmitting_controls:
            led.off()
            led.close()
        for led in self._deafened_controls:
            led.off()
            led.close()
        for led in self._recieving_controls:
            led.off()
            led.close()
        self._buttons = []
        self._connected_controls = []
        self._transmitting_controls = []
        self._deafened_controls = []
        self._recieving_controls = []

    @property
    def transmitting(self) -> bool:
        '''
        When true, audio information form the microphone will be sent to the mumble server.
        '''
        return self._transmitting

    @transmitting.setter
    def transmitting(self, value: bool):
        if not self.transmitting and value:
            print("Started transmitting")
            self._transmitting = True
            for led in self._transmitting_controls:
                led.on()
        elif self.transmitting and not value:
            print("Stopped transmitting")
            self._transmitting = False
            for led in self._transmitting_controls:
                led.off()

    @property
    def deafened(self) -> bool:
        '''
        When true, audio information recieved from the mumble server will be ignored.
        '''
        return self._deafened

    @deafened.setter
    def deafened(self, value: bool):
        if not self._deafened and value:
            print("Started deafening")
            self._deafened = True
            for led in self._deafened_controls:
                led.on()
        elif self._deafened and not value:
            print("Stopped deafening")
            self._deafened = False
            for led in self._deafened_controls:
                led.off()


    @property
    def recieving(self) -> bool:   
        '''
        When true, indicates that audio information has been recieved from the mumble server and is being played on the local speakers.
        ''' 
        return self._recieving

    @recieving.setter
    def recieving(self, value: bool):
        if not self._recieving and value:
            self._recieving = True
            for led in self._recieving_controls:
                led.on()
        elif self._recieving and not value:
            self._recieving = False
            for led in self._recieving_controls:
                led.off()

    @property
    def connected(self) -> bool:
        '''
        When true, indicates that the intercom is connected to a mumble server.
        '''
        return self._connected

    def _set_connected(self):
        self._connected = True
        for led in self._connected_controls:
            led.on()

    def _set_disconnected(self):
        self._connected = False
        for led in self._connected_controls:
            led.off()
    