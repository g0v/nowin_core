
class AudioStream(object):

    """Audio stream

    """

    def __init__(self, blockSize=1024, blockCount=128, base=0):
        """

        The bytes is a big memory chunk, it buffers all incoming audio data.
        There are blocks in the memory chunk, they are the basic unit to send
        to peer.

        <-------------- Memory chunk ------------------>
        <--Block1--><--Block2--><--Block3--><--Block4-->
        ^          ^          ^          ^
        L1         L2         L3         L4

        We map blocks to the real audio stream

        <------------------ Audio Stream -------------->  ---> time goes
        <--Block3--><--Block4--><--Block1--><--Block2-->

                          Map to

        <-------------- Memory chunk ------------------>
        <--Block1--><--Block2--><--Block3--><--Block4-->

        Every listener got their offset of whole audio stream, so that we can
        know which block he got.

        ------------<------------------ Audio Stream --------------> --->
                    <--Block3--><--Block4--><--Block1--><--Block2-->
        ^
        L5

        When there is a listener point to a out of buffer window place, we
        should move the pointer to the first current block.

        ------------<------------------ Audio Stream --------------> --->
                    <--Block3--><--Block4--><--Block1--><--Block2-->
                    ^
                    L5

        @param blockSize: size of block
        @param blockCount: count of blocks
        """
        self._blockSize = blockSize
        self._blockCount = blockCount
        self._bufferSize = blockSize * blockCount

        #: base address of buffering windows
        self._base = base
        #: total size of written data in blocks (not include chunk pieces)
        self._size = base
        #: bytes array
        self._bytes = bytearray(self.bufferSize)
        #: small chunks, they are not big enough to fit a block
        self._pieces = []
        #: total size of pieces
        self._pieceSize = 0

    def _getBlockSize(self):
        return self._blockSize
    blockSize = property(_getBlockSize)

    def _getBlockCount(self):
        return self._blockCount
    blockCount = property(_getBlockCount)

    def _getBufferSize(self):
        return self._bufferSize
    bufferSize = property(_getBufferSize)

    def _getBase(self):
        return self._base
    base = property(_getBase)

    def _getSize(self):
        return self._size
    size = property(_getSize)

    def _getBuffer(self):
        return str(self._bytes)
    buffer = property(_getBuffer)

    def _getMiddle(self):
        """Address of middle block

        """
        return self.base + (((self.size - self.base) / self.blockSize) / 2) * \
            self.blockSize
    middle = property(_getMiddle)

    def _getData(self):
        """Get current audio data we have in correct order

        for example, we have 3 blocks

        <--Block 3--><--Block 1--><--Block 2-->

        and some extra not integrated data pieces

        <--Chunk-->

        Then we should get

        <--Block 1--><--Block 2--><--Block3--><--Chunk-->

        as result
        """
        # total bytes we have in the buffer (as blocks)
        total = self.size - self.base
        # the begin offset of first block in buffer
        begin = self.base % self.bufferSize
        # the tail part
        tail = self._bytes[begin:total]
        # the head part
        head = self._bytes[0:begin]
        # not integrated chunk
        chunk = ''.join(self._pieces)
        return tail + head + chunk
    data = property(_getData)

    def write(self, chunk):
        """Write audio data to audio stream

        @param chunk: audio data chunk to write
        """
        # append chunk to pieces
        self._pieces.append(chunk)
        self._pieceSize += len(chunk)

        while self._pieceSize >= self.blockSize:
            whole = ''.join(self._pieces)
            block = whole[:self.blockSize]
            # there is still some remaining piece
            if self._pieceSize - self.blockSize > 0:
                self._pieces = [whole[self.blockSize:]]
                self._pieceSize = len(self._pieces[0])
            else:
                self._pieces = []
                self._pieceSize = 0

            # write the block to buffer
            begin = self.size % self.bufferSize
            oldSize = len(self._bytes)
            self._bytes[begin:begin + self.blockSize] = block
            assert len(self._bytes) == oldSize, "buffer size is changed"

            self._size += len(block)
            delta = self.size - self.base
            # if the base out of buffer window, move it to begin of window
            if delta > self.bufferSize:
                self._base = self.size - self.bufferSize

    def read(self, offset, no_copy=False):
        """Read a block from audio stream

        @param offset: offset to read block
        @return: (block, new offset)
        """
        # we don't have new data
        if offset >= self.size:
            return None, offset
        # out of window
        if offset < self.base:
            offset = self.middle
        begin = offset % self.bufferSize
        assert begin >= 0
        assert begin < self.bufferSize
        if no_copy:
            block = buffer(self._bytes, begin, self.blockSize)
        else:
            block = str(self._bytes[begin:begin + self.blockSize])
        offset += self.blockSize
        return block, offset
