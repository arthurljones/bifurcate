#!/usr/bin/env python3

# TODO: Color pixels based on (normalized) iteration count before stabilization (if any)
# TODO: Further optimize calcNext (bulk of render time spent there at useful subsampling values)
# TODO: Bias zoom around current mouse position
# TODO: screenToValue and valueToScreen methods

import collections, time
import pygame as pg
import numpy as np
from pygame.locals import *
from pygame import Rect
from math import ceil

class Bifurcate: 
    def __init__(self):
        pg.init()

        self.width = 1280
        self.height = 768
        self.screen = pg.display.set_mode((self.width, self.height))
        self.clock = pg.time.Clock()
        self.startI = 0.0
        self.endI = 1.0
        self.startR = 2.0
        self.endR = 4.0
        self.currR = None
        self.lastX = 0
        self.subsample = 1.0
        self.values = np.zeros((self.width, self.height))
        self.pixels = None
        self.mouseDown = None
        self.mouseDrag = None
        self.done = False

        pg.display.set_caption('bifurcate')
        background = pg.Surface(self.screen.get_size())
        background = background.convert()
        background.fill((0, 0, 0))
        self.screen.blit(background, (0, 0))
        pg.display.flip()

        self.recalc()

    def domain(self):
        return self.endR - self.startR

    def range(self):
        return self.endI - self.startI

    def currX(self):
        if self.currR is None:
            return self.width
        else:
            return (self.currR - self.startR) / self.domain() * self.width

    def calcNext(self):
        if self.currR is None:
            return False

        rawX = self.currX()
        x0 = int(rawX)
        x1 = x0 + 1
        px1 = rawX - x0
        px0 = 1 - px1
        value = 0.5


        for n in range(100):
            value = value * self.currR * (1.0 - value)

        sampleStep = 1.0 / self.subsample
        fill = None
        # Erase ahead of where we'll be drawing if we've crossed into a new column
        if rawX - sampleStep < x0 and x0 < self.width:
            nextEnd = min(ceil(x0 + sampleStep), self.width - 1)
            self.values[x0:nextEnd].fill(0.0)

        lastVals = collections.deque(maxlen = 32)
        drawnCount = 0
        for n in range(int(self.height * self.subsample)):
            value = value * self.currR * (1.0 - value)

            # TODO: Draw over range for subsample < 1.0
            # Split value between adjacent pixels
            rawY = (value - self.startI) / self.range() * self.height
            y0 = int(rawY)
            y1 = y0 + 1
            py1 = rawY - y0
            py0 = 1 - py1

            drawn = False
            if (x0 >= 0 and x0 < self.width):
                if (y0 >= 0 and y0 < self.height):
                    drawn = True
                    self.values[x0][y0] += px0 * py0
                if (y1 >= 0 and y1 < self.height):
                    drawn = True
                    self.values[x0][y1] += px0 * py1
            if (x1 >= 0 and x1 < self.width):
                if (y0 >= 0 and y0 < self.height):
                    drawn = True
                    self.values[x1][y0] += px1 * py0
                if (y1 >= 0 and y1 < self.height):
                    drawn = True
                    self.values[x1][y1] += px1 * py1

            if drawn:
                drawnCount += 1

                # Early exit for small-count columns
                if drawnCount <= len(lastVals) + 1:
                    done = False
                    for lastVal in lastVals:
                        if abs(lastVal - value) < 10e-8:
                            done = True
                            break
                    if done:
                        break

                    lastVals.append(value)

        self.currR += self.domain() / (self.width * self.subsample)
        if self.currR > self.endR:
            self.currR = None

        return True

    def recalc(self):
        self.currR = self.startR
        self.calcStart = time.time()

        dim = f"{self.width}x{self.height}"
        domain = f"[{round(self.startR, 4)}, {round(self.endR, 4)}] ({self.domain()})"
        range = f"[{round(self.startI, 4)}, {round(self.endI, 4)}] ({self.range()})"
        sub = f"{self.subsample}x"
        print(f"Drawing {dim} in domain {domain}, range {range}  at {sub} subsampling")
        
    def draw(self, valuesChanged = False):
        if self.pixels is None or valuesChanged:
            self.pixels = np.zeros((self.width, self.height), dtype = int)
            for x, column in enumerate(self.values):
                norm = np.flip(((column - np.min(column)) / np.ptp(column) * 255)).astype(int)
                self.pixels[x] = norm + np.left_shift(norm, 8) + np.left_shift(norm, 16)

            cx = int(self.currX()) + 1
            if cx < self.width:
                self.pixels[cx].fill(0x007FFF7F)

        pg.surfarray.blit_array(self.screen, self.pixels)

        if self.mouseDrag:
            pg.draw.rect(self.screen, (127, 127, 255), self.mouseDrag, 1)

        pg.display.flip()

    def mouseMove(self, pos):
        if self.mouseDown:
            dx, dy = self.mouseDown
            cx, cy = pos
            top = min(dy, cy)
            left = min(dx, cx)
            bottom = max(dy, cy)
            right = max(dx, cx)
            self.mouseDrag = Rect(left, top, right - left, bottom - top)
            print(self.mouseDrag)
        else:
            self.mouseDrag = None

    def boxZoom(self, rect):
        if rect and rect.width > 1 and rect.height > 1:
            startR = self.startR
            startI = self.startI
            domain = self.domain()
            range = self.range()

            self.startR = startR + float(rect.left) / self.width * domain
            self.endR = startR + float(rect.right) / self.width * domain

            self.startI = startI + (self.height - float(rect.bottom)) / self.height * range
            self.endI = startI + (self.height - float(rect.top)) / self.height * range

            self.clampViewport()
            self.recalc()

    def scaleZoom(self, scale):
        domain = self.domain()
        range = self.range()

        halfScale = (1 - scale) / 2
        self.startR += domain * halfScale
        self.endR -= domain * halfScale
        self.startI += range * halfScale
        self.endI -= range * halfScale

        self.clampViewport()
        self.recalc()

    def clampViewport(self):
        quantum = 10e-9
        self.startR = max(min(self.startR, 4.0 - quantum), 1.0)
        self.endR = max(min(self.endR, 4.0), self.startR + quantum)
        self.startI = max(min(self.startI, 1.0 - quantum), 0.0)
        self.endI = max(min(self.endI, 1.0), self.startI + quantum)

    def handleEvent(self, event):
        if event.type == QUIT:
            self.done = True

        elif event.type == KEYUP:
            if event.key == K_ESCAPE or event.key == K_q or \
                    (event.key == K_c and event.mod & KMOD_CTRL):
                self.done = True

            if event.key == K_UP:
                self.subsample *= 2.0
                self.recalc()

            if event.key == K_DOWN:
                self.subsample /= 2.0
                self.recalc()

        elif event.type == pg.MOUSEMOTION:
            self.mouseMove(event.pos)

        elif event.type == MOUSEBUTTONDOWN:
            self.mouseMove(event.pos)
            if event.button == 1:
                self.mouseDown = event.pos

        elif event.type == MOUSEBUTTONUP:
            self.mouseMove(event.pos)
            rest = self.endR - self.startR
            
            recalc = False
            if event.button == 1: # Left Click
                if self.mouseDrag:
                    self.boxZoom(self.mouseDrag)
                self.mouseDown = None
                self.mouseDrag = None

            elif event.button == 4: # Scroll Down
                self.scaleZoom(0.75)

            elif event.button == 5: # Scroll Up
                self.scaleZoom(1.33)

    def tick(self):
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

        for event in pg.event.get():
            self.handleEvent(event)

        self.draw(changed)
        lastTicks = self.clock.tick(30)

    def mainLoop(self):
        while not self.done:
            self.tick()

if __name__ == "__main__":
    Bifurcate().mainLoop()
