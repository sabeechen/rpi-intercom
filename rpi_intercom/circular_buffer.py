import numpy as np

class Buffer:
    """
    Implenets a circular queue, but optimized around inserting and removing
    chunks of data at a time.  This makes all the indexing logic suprisingly
    intricate but hey, its fast.  Necessary because python isnt's well know
    for its speed in loops all the iterative logic is delegated to numpy,
    which should be fast.  Or maybe I'm pre-optimizing.  Its not like I ran
    benchmarks.  
    """
    def __init__(self, length: int):
        self.max_length: int = length
        self.arr = np.zeros(self.max_length, dtype=np.float)
        self.start: int = 0
        self.length: int = 0

    def push(self, data: np.ndarray):
        from_start = 0
        from_length = len(data)
        if from_length >= self.max_length:
            # easy case, fill the whole array and reset
            self.arr[0:self.max_length] = data[-self.max_length:]
            self.start = 0
            self.length = self.max_length
            return

        # We might truncate from the end if we add all these items.  If so, adjust the array
        truncate = from_length + self.length - self.max_length
        if truncate > 0:
            self.length -= truncate
            self.start = (self.start + truncate) % self.max_length

        first_start = (self.start + self.length) % self.max_length
        first_end = min(first_start + from_length, self.max_length)
        first_length = first_end - first_start

        self.arr[first_start:first_start + first_length] = data[from_start: from_start + first_length]
        if first_length < from_length:
            delta = from_length - first_length
            self.arr[0: delta] = data[from_start + first_length: from_start + first_length + delta]

        self.length += from_length

    def read(self, amount: int) -> np.ndarray:
        if amount > self.length:
            amount = self.length
        ret = np.zeros(amount)
        first_end = amount + self.start
        first_length = amount
        if first_end > self.max_length:
            first_length = self.max_length - self.start
            first_end = self.max_length
        if first_end - self.start > amount:
            first_end = self.start + amount
        ret[0:first_length] = self.arr[self.start:first_end]
        ret[first_length:] = self.arr[0:amount-first_length]
        return ret

    def pop(self, amount: int):
        ret = self.read(amount)
        amount = len(ret)
        if amount == self.length:
            self.start = 0
            self.length = 0
        else:
            self.length -= amount
            self.start = (self.start + amount) % self.max_length
        return ret
        
        
