from itertools import islice, chain

def highlight_parts(text, highlight, chars=['^', '~', '-', '!']):
    """Highlights certain parts in a text with special markup::

          text = '''
          Lorem ipsum dolor si amet
                ^^^^^ ~~~~~    ^^^^
          consectetur adipiscing elit
          Mauris ac magna a nisl ornare
                 --------   !!!!
          '''
          highlight_parts(text, lambda x, c: '<strong>' + x + '</strong>')

    """
    highlight_fn = lambda x, char: x if char == ' ' else highlight(x, char)
    chars = frozenset(chain([' '], chars))
    lines = text.splitlines()
    # We need to reverse lines to parse the markers before
    # encountering the line that should be highlighting
    lines.reverse()
    result = []
    highlights = []
    for line in lines:
        # If line contains highlight markup we collect all
        # tuples (start, stop) in a list called highlights
        # This also contains spaces, which is a highlight
        # that doesn't highlight ;)
        if line and all(x in chars for x in line):
            search_chars = chars
            last_pos = 0
            while True:
                pos, c = find_char(line, search_chars, last_pos)
                if pos == -1:
                    break
                last_pos = pos
                highlights += (pos, c)
                search_chars = chars - set([c])
            highlights.append(len(line))
            # Tupelize: [1, '^', 7 '!', 9] => [('^', 1, 7), ('!', 7, 9)]
            highlights = zip(*(islice(highlights, start, None, 2)
                                for start in (1, 0, 2)))
        else:
            # If previous line contained slices, we slice that
            # line and apply marking function to relevant parts
            highlights = highlights or [(' ', 0, len(line))]
            # Add empty highlight if text line is shorter than marker line
            if highlights[-1][2] < len(line):
                highlights.append((' ', highlights[-1][2], len(line)))
            result.append(''.join([highlight_fn(line[h:next_h], c)
                                   for c, h, next_h in highlights]))
            highlights = []
    return u'\n'.join(reversed(result))

def find_char(some_str, chars, last_pos=0):
    for i in xrange(last_pos, len(some_str)):
        c = some_str[i]
        if c in chars:
            return (i, c)
    return (-1, None)
