#!/usr/bin/env python3

# TODO: Color pixels based on (normalized) iteration count before stabilization (if any)
# TODO: Further optimize calcNext (bulk of render time spent there at useful subsampling values)

import pygame, collections, time
import numpy as np
import pygame.surfarray as surfarray
from pygame.locals import *
from math import ceil

class Bifurcate: 
    def __init__(self):
        pygame.init()

        self.width = 1280
        self.height = 768
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.clock = pygame.time.Clock()
        self.startR = 2.0
        self.endR = 4.0
        self.currR = None
        self.lastX = 0
        self.subsample = 1.0
        self.values = np.zeros((self.width, self.height))

        pygame.display.set_caption('bifurcate')
        background = pygame.Surface(self.screen.get_size())
        background = background.convert()
        background.fill((0, 0, 0))
        self.screen.blit(background, (0, 0))
        pygame.display.flip()

        self.recalc()

    def domainWidth(self):
        return self.endR - self.startR

    def currX(self):
        if self.currR is None:
            return self.width
        else:
            return (self.currR - self.startR) / self.domainWidth() * self.width

    def calcNext(self):
        if self.currR is None:
            return False

        rawX = self.currX()
        x = int(rawX)
        paramX = rawX - x
        value = 0.5

        for n in range(100):
            value = value * self.currR * (1.0 - value)

        sampleStep = 1.0 / self.subsample
        fill = None
        # Erase ahead of where we'll be drawing if we've crossed into a new column
        if rawX - sampleStep < x and x < self.width:
            nextEnd = min(ceil(x + sampleStep), self.width - 1)
            self.values[x:nextEnd].fill(0.0)

        lastVals = collections.deque(maxlen = 8)
        for i, n in enumerate(range(int(self.height * self.subsample))):
            value = value * self.currR * (1.0 - value)

            # TODO: Draw over range for subsample < 1.0
            # Split value between adjacent pixels
            rawY = value * self.height
            y = int(rawY)
            paramY = rawY - y
            if (x < self.width):
                if (y < self.height):
                    self.values[x][y] += (1 - paramY) * (1 - paramX)
                if (y + 1 < self.height):
                    self.values[x][y+1] += paramY * (1 - paramX)
            if (x + 1 < self.width):
                if (y < self.height):
                    self.values[x+1][y] += (1 - paramY) * (paramX)
                if (y + 1 < self.height):
                    self.values[x+1][y+1] += paramY * (paramX)


            # Early exit for small-count columns
            if i <= len(lastVals) + 1:
                done = False
                for lastVal in lastVals:
                    if abs(lastVal - value) < 10e-8:
                        done = True
                        break
                if done:
                    break

                lastVals.append(value)

        self.currR += self.domainWidth() / (self.width * self.subsample)
        if self.currR > self.endR:
            self.currR = None

        return True

    def recalc(self):
        self.currR = self.startR
        self.calcStart = time.time()

        dim = f"{self.width}x{self.height}"
        domain = f"[{round(self.startR, 4)}, {round(self.endR, 4)}]"
        sub = f"{self.subsample}x"
        print(f"Drawing {dim} in {domain} at {sub} subsampling")
        
    def draw(self):
        pixels = np.zeros((self.width, self.height), dtype = int)
        for x, column in enumerate(self.values):
            norm = np.flip(((column - np.min(column)) / np.ptp(column) * 255)).astype(int)
            pixels[x] = norm + np.left_shift(norm, 8) + np.left_shift(norm, 16)

        cx = int(self.currX()) + 1
        if cx < self.width:
            pixels[cx].fill(0x007FFF7F)

        pygame.surfarray.blit_array(self.screen, pixels)
        pygame.display.flip()

    def tick(self):
        lastTicks = self.clock.tick(30)
        
        maxFrameTime = 1.0 / 10.0
        changed = False
        finished = False
        start = time.time()
        while time.time() - start < maxFrameTime:
            finished = not self.calcNext()
            if finished:
                break
            else:
                changed = True

        if changed:
            if finished:
                calcTime = time.time() - self.calcStart
                print(f"Calculating... Done in {round(calcTime, 2)}s")
            else:
                percent = str(int(self.currX() * 100.0 / self.width)).rjust(3,' ')
                print(f"Calculating... {percent}%\r", end = '')

            self.draw()


        for event in pygame.event.get():
            if event.type == QUIT:
                return True

            if event.type == KEYUP:
                if event.key == K_ESCAPE or event.key == K_q or \
                        (event.key == K_c and event.mod & KMOD_CTRL):
                    return True

                if event.key == K_UP:
                    self.subsample *= 2.0
                    self.recalc()

                if event.key == K_DOWN:
                    self.subsample /= 2.0
                    self.recalc()

            elif event.type == MOUSEBUTTONUP:
                rest = self.endR - self.startR
                
                redraw = False
                if event.button == 4:
                    rest *= 0.75
                    redraw = True
                elif event.button == 5:
                    rest *= 1.33
                    redraw = True

                if redraw:
                    self.startR = max(min(self.endR - rest, 4.0), -2.0)
                    self.recalc()

    def mainLoop(self):
        while True:
            if self.tick():
                return

if __name__ == "__main__":
    Bifurcate().mainLoop()
