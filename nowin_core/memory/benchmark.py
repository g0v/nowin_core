import os
import random
import time

from nowin_core.memory import audio_stream


class Object(object):

    def __init__(self):
        self.dead = False
        self.children = set()

    def addChild(self, child):
        self.children.add(child)
        print len(self.children)

    def update(self, elapsed):
        self.updateChildren(elapsed)

    def updateChildren(self, elapsed):
        for child in self.children.copy():
            child.update(elapsed)
            if child.dead:
                self.children.remove(child)

    def markDead(self):
        self.dead = True


class Radio(Object):

    def __init__(self):
        Object.__init__(self)
        self.aduo_stream = audio_stream.AudioStream(4096, 32)
        print 'Create radio %r' % self

    def update(self, elapsed):
        r = random.random()
        if r < 0.02:
            self.aduo_stream.write(os.urandom(random.randint(300, 400)))
            for i in range(1, random.randint(1, 200)):
                self.aduo_stream.read(self.aduo_stream.base)
        r = random.random()
        if r < 0.0001:
            self.close()
        self.updateChildren(elapsed)

    def close(self):
        print 'Remove radio %r' % self
        self.markDead()


def main():
    world = Object()
    while True:
        r = random.random()
        if r < 0.02:
            radio = Radio()
            world.addChild(radio)
        world.update(0.001)
        time.sleep(0.001)

if __name__ == '__main__':
    main()
