#!/usr/bin/env python3

#TODO: Subsample on x axis, and/or subpixel line size
#TODO: Run bifurcate calculation in a thread

import pygame, collections, math, numpy
import pygame.surfarray as surfarray
from pygame.locals import *

INITIAL_ITERATIONS = 1000
WHITE = 0xFFFFFF

class Bifurcate: 
    def __init__(self):
        pygame.init()

        self.width = 1280
        self.height = 768
        self.iteration = 0
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.clock = pygame.time.Clock()

        pygame.display.set_caption('bifurcate')
        background = pygame.Surface(self.screen.get_size())
        background = background.convert()
        background.fill((64, 64, 64))
        self.screen.blit(background, (0, 0))
        pygame.display.flip()

        self.surf = surfarray.pixels2d(self.screen)

    def draw(self, x, y, param):
        if x >= 0 and x < self.width and y >= 0 and y < self.height:
            val = self.surf[x, y] 
            self.surf[x, y] = max(int(val + (1.0 - param) * WHITE), WHITE)

    def bifurcate(self, x):
        drawn = set()
        value = 0.5
        r = x * 4.0 / (self.width)

        print(f"bifurcate {x} r: {r}")

        for n in range(INITIAL_ITERATIONS):
            value = value * r * (1.0 - value)

        for n in range(self.height):
            value = value * r * (1.0 - value)
            
            scaled = round(value, 6) * self.height
            if not scaled in drawn:
                drawn.add(scaled)
                y = int(scaled)
                param = scaled - y
                self.draw(x, y, 1 - param)
                self.draw(x, y + 1, param)

    def tick(self):
        self.clock.tick(60)
        for event in pygame.event.get():
            if event.type == QUIT:
                return True
            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                return True

        for n in range(5):
            if (self.iteration < self.width):
                x = self.iteration
                self.bifurcate(x)
                self.iteration += 1

        pygame.display.flip()

    def mainLoop(self):
        while True:
            if self.tick():
                return

if __name__ == "__main__":
    Bifurcate().mainLoop()
