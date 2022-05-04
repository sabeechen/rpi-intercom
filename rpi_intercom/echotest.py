class EchoTest():
    '''
    A simple class that plays audio recived from the micrphone 
    back on the speaker.  Useful for testing echo cancellation.  
    '''
    def __init__(self):
        self.sound_callback = None

    def transmit(self, chunk):
        if self.sound_callback:
            self.sound_callback(chunk)

    def start(self):
        pass

    def stop(self):
        pass