class LineParser(object):

    def __init__(self, newline='\r\n', remain=''):
        self.newline = newline
        self._buffer = [remain]
        self._size = len(remain)

    def feed(self, data):
        self._buffer.append(data)
        self._size += len(data)

    def getLine(self):
        data = ''.join(self._buffer)
        index = data.find(self.newline)
        if index != -1:
            line = data[:index]
            self._buffer = [data[index + len(self.newline):]]
            self.length = len(self._buffer[0])
            return line

    def iterLines(self):
        line = self.getLine()
        while line is not None:
            yield line
            line = self.getLine()
