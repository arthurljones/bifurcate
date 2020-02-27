#!/usr/bin/env python3

# TODO: Color pixels based on (normalized) iteration count before stabilization (if any)
# TODO: X subsampling for columns (requires holding multiple columns in memory until done)

import pygame, collections, math, numpy, threading, queue
import pygame.surfarray as surfarray
from pygame.locals import *

INITIAL_ITERATIONS = 1000
WHITE = 0xFFFFFF

class Calculator:
    def __init__(self, resolutionX, resolutionY, startX = 0.0, startY = 0.0,
            endX = 4.0, endY = 1.0):
        self.startTime = pygame.time.get_ticks()
        self.round = 7
        self.startX = startX
        self.startY = startY
        self.domainScale = endX - startX
        self.endX = endX
        self.endY = endY
        self.resolutionX = resolutionX
        self.resolutionY = resolutionY
        self.queue = queue.Queue()
        self.done = False
        self.thread = threading.Thread(target = self.calculate)
        self.thread.start()

    def calculate(self):
        for r in numpy.arange(self.startX, self.endX, self.domainScale / self.resolutionX):
            value = 0.5

            prelim = set()
            for n in range(INITIAL_ITERATIONS):
                value = value * r * (1.0 - value)
                rounded = round(value, self.round)
                if rounded in prelim:
                    break
                prelim.add(rounded)

            if self.done:
                print("Calculator: early return")
                return

            result = set()
            for n in range(self.resolutionY):
                value = value * r * (1.0 - value)
                rounded = round(value, self.round)
                if rounded in result:
                    break
                result.add(rounded)

            self.queue.put_nowait((r, sorted(list(result))))

            if self.done:
                print("Calculator: early return")
                return

        print(f"Calculator done in {pygame.time.get_ticks() - self.startTime} ms")
        self.done = True

class Bifurcate: 
    def __init__(self):
        pygame.init()

        self.width = 1280
        self.height = 768
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.clock = pygame.time.Clock()
        self.startX = 2.0

        pygame.display.set_caption('bifurcate')
        background = pygame.Surface(self.screen.get_size())
        background = background.convert()
        background.fill((16, 16, 16))
        self.screen.blit(background, (0, 0))
        pygame.display.flip()
        self.calculator = None

        self.surf = surfarray.pixels2d(self.screen)
        self.calculate()

    def calculate(self):
        if self.calculator:
            self.calculator.done = True
        self.calculator = Calculator(self.width, self.height * 2, startX = self.startX)

    def drawColumn(self, x, values):
        if x < 0 or x >= self.width:
            return

        column = numpy.zeros(self.height)
        drawn = set()
        maxValues = self.calculator.resolutionY 
        ceiling = (maxValues - len(values)) / maxValues
        for value in values:
            scaled = value * self.height
            if not scaled in drawn:
                drawn.add(scaled)
                y = int(scaled)
                param = scaled - y
                if (y < len(column)):
                    column[y] += 1 - param
                if (y +1 < len(column)):
                    column[y+1] += param

        colMax = numpy.max(column)
        colMin = numpy.min(column)
        range = colMax - colMin
        mean = numpy.mean(column)

        normalizer = numpy.vectorize(lambda x: (x - colMin) / range * 0xFF)
        normalized = normalizer([column])
        
        iter = numpy.nditer(normalized)
        y = 0
        for val in iter:
            intVal = int(val)
            color = intVal | intVal << 8 | intVal << 16
            self.surf[x, self.height - y - 1] = color
            y += 1


    def tick(self):
        start = pygame.time.get_ticks()
        while True:
            try:
                rawX, column = self.calculator.queue.get_nowait()
                x = (rawX - self.calculator.startX) / self.calculator.domainScale * self.width
                self.drawColumn(int(x), column)
            except queue.Empty:
                #print("Queue empty")
                break

            if (pygame.time.get_ticks() - start > (1000.0 / 60.0)):
                #print("Used up time drawing")
                break
                    
        self.clock.tick(60)
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                return True

            elif event.type == MOUSEBUTTONUP:
                rest = self.calculator.endX - self.startX
                
                redraw = False
                if event.button == 4:
                    rest *= 0.75
                    redraw = True
                elif event.button == 5:
                    rest *= 1.33
                    redraw = True

                if redraw:
                    self.startX = max(min(self.calculator.endX - rest, 4.0), -2.0)
                    self.calculate()

        pygame.display.flip()

    def mainLoop(self):
        try: 
            while True:
                if self.tick():
                    return
        finally:
            if self.calculator:
                self.calculator.done = True


if __name__ == "__main__":
    Bifurcate().mainLoop()
