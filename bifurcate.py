#!/usr/bin/env python3

# TODO: Color pixels based on (normalized) iteration count before stabilization (if any)
# TODO: X subsampling for columns (requires holding multiple columns in memory until done)

import pygame, collections, time
import numpy as np
import pygame.surfarray as surfarray
from pygame.locals import *

class Bifurcate: 
    def __init__(self):
        pygame.init()

        self.width = 1280
        self.height = 768
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.clock = pygame.time.Clock()
        self.startX = 2.0
        self.endX = 4.0

        pygame.display.set_caption('bifurcate')
        background = pygame.Surface(self.screen.get_size())
        background = background.convert()
        background.fill((16, 16, 16))
        self.screen.blit(background, (0, 0))
        pygame.display.flip()

        self.surf = surfarray.pixels2d(self.screen)

        self.columns = self.genColumns()

    def drawColumn(self, x, column):
        if x < 0 or x >= self.width:
            return

        colMax = np.max(column)
        colMin = np.min(column)
        range = colMax - colMin
        #mean = np.mean(column)

        normalizer = np.vectorize(lambda x: (x - colMin) / range * 0xFF)
        normalized = normalizer([column])

        iter = np.nditer(normalized)
        y = 0
        for val in iter:
            if not np.isfinite(val):
                continue
            intVal = int(val)
            color = intVal | intVal << 8 | intVal << 16
            self.surf[x, self.height - y - 1] = color
            y += 1

    def domainWidth(self):
        return self.endX - self.startX

    def genColumns(self, startY = 0.0, endY = 1.0):
        subsampleY = 4.0

        for r in np.arange(self.startX, self.endX, self.domainWidth() / self.width):
            value = 0.5

            for n in range(100):
                value = value * r * (1.0 - value)

            lastVals = collections.deque(maxlen = 16)
            column = np.zeros(self.height)
            for i, n in enumerate(range(int(self.height * subsampleY))):
                value = value * r * (1.0 - value)

                # Paint on adjacent pixels
                scaled = value * self.height
                y = int(scaled)
                param = scaled - y
                if (y < len(column)):
                    column[y] += 1 - param
                if (y +1 < len(column)):
                    column[y+1] += param

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

            yield (r, column)

    def tick(self):
        start = pygame.time.get_ticks()
        maxFrameTicks = (1000.0 / 60.0)
        calcTime = 0.0
        drawTime = 0.0
        while self.columns and pygame.time.get_ticks() - start < maxFrameTicks:
            calcStart = time.time()
            result = next(self.columns, None)
            if not result:
                self.columns = None
                break

            r, column = result
            x = (r - self.startX) / self.domainWidth() * self.width
            calcTime += time.time() - calcStart

            drawStart = time.time()
            self.drawColumn(int(x), column)
            drawTime += time.time() - drawStart

        if drawTime > 0.0:
            print(f"calc/draw ratio: {calcTime / drawTime}")

        self.clock.tick(60)
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                return True

            elif event.type == MOUSEBUTTONUP:
                rest = self.endX - self.startX
                
                redraw = False
                if event.button == 4:
                    rest *= 0.75
                    redraw = True
                elif event.button == 5:
                    rest *= 1.33
                    redraw = True

                if redraw:
                    self.startX = max(min(self.endX - rest, 4.0), -2.0)
                    self.columns = self.genColumns()

        pygame.display.flip()

    def mainLoop(self):
        while True:
            if self.tick():
                return


if __name__ == "__main__":
    Bifurcate().mainLoop()
