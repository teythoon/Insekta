from __future__ import division
import sys
from functools import wraps

def consumer(fn):
    """Wrap a generator that received value and start it by calling next()."""
    @wraps(fn)
    def start_generator(*args, **kwargs):
        generator = fn(*args, **kwargs)
        generator.next()
        return generator
    return start_generator

@consumer
def progress_bar(maximum, length=74):
    """Return a progress bar generator. Use .send() to send current value.

    :param maximum: The value that will be 100%
    :length: The length of the progress bar in number of characters
    """
    bar_length = length - 2
    last_num_hashes = None
    while True:
        current = (yield)
        if current is None:
            sys.stdout.write('\033[{0}C'.format(length))
            sys.stdout.flush()
            yield # Convenient interface to prevent catching a StopIteration
            break
        num_hashes = int((current / maximum) * (length - 2))
        num_spaces = bar_length - num_hashes
        if num_hashes != last_num_hashes:
            sys.stdout.write('\033[s\033[2K') # save cursor and clear line
            sys.stdout.write('[{0}{1}]'.format('#' * num_hashes, '-' * num_spaces))
            sys.stdout.write('\033[u') # restore cursor
            sys.stdout.flush()
        last_num_hashes = num_hashes
