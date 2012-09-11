from renderer import LevelCamera

from lib2d.buttons import *
from lib2d.signals import *
from lib2d.physics import euclid
from lib2d import res, ui, gfx, context

import pygame, math, time


"""
FUTURE:
    Create immutable types when possible to reduce headaches when threading
"""

debug = 1
movt_fix = 1/math.sqrt(2)


def getNearby(thing, d):
    p = thing.parent
    body = p.getBody(thing)
    bbox = body.bbox.inflate(64,d,d)
    x1, y1, z1 = body.bbox.center
    nearby = []
    for other in p.testCollideObjects(bbox, skip=[body]): 
        x2, y2, z2 = other.bbox.center
        dist = math.sqrt(pow(x1-x2, 2) + pow(y1-y2, 2) + pow(z1-z2, 2))
        nearby.append((d, (other.parent, other)))

    return [ i[1] for i in sorted(nearby) ]


class SoundManager(object):
    def __init__(self):
        self.sounds = {}
        self.last_played = {}

    def loadSound(self, filename):
        self.sounds[filename] = res.loadSound(filename)
        self.last_played[filename] = 0

    def play(self, filename, volume=1.0):
        now = time.time()
        if self.last_played[filename] + .05 <= now:
            self.last_played[filename] = now
            sound = self.sounds[filename]
            sound.set_volume(volume)
            sound.play()

    def unload(self):
        self.sounds = {}
        self.last_played = {}


SoundMan = SoundManager()



class LevelUI(ui.UserInterface):
    pass



class LevelState(context.Context):
    """
    This state is where the player will move the hero around the map
    interacting with npcs, other players, objects, etc.

    much of the work done here is in the Standard UI class.
    """

    def __init__(self, parent, area):
        super(LevelState, self).__init__(parent)
        self.area = area
        self.hero = area.getChildByGUID(1)
        self.hero_body = self.area.getBody(self.hero)

        # awkward input handling
        self.wants_to_stop_on_landing = False
        self.input_changed = False
        self.jumps = 0


    def activate(self):
        self.ui = LevelUI()
        vpm = ui.Frame(self.ui, ui.GridPacker())
        vp = ui.ViewPort(self.ui, self.area)
        vpm.addElement(vp)
        self.ui.addElement(vpm)
        self.ui.rect = gfx.get_rect()

        self.camera = vp.camera


    def update(self, time):
        self.area.update(time)

        if self.input_changed:
            self.input_changed = False

            if self.hero_body.vel.z == 0:

                if self.wants_to_stop_on_landing:
                    self.wants_to_stop_on_landing = False
                    self.hero_body.vel.y = 0
                else:
                    self.hero_body.vel.y = self.player_vector[1]

                if self.hero_body.vel.y == 0:
                    self.hero.avatar.play("stand")

                elif abs(self.hero_body.vel.y) < 1.0:
                    self.hero.avatar.play("walk")

                #else:
                #    self.hero.avatar.play("run")


    def draw(self, surface):
        self.camera.center(self.hero_body.bbox.center)
        self.ui.draw(surface)


    def handle_commandlist(self, cmdlist):
        #self.ui.handle_commandlist(cmdlist)
        self.handleMovementKeys(cmdlist)


    def handleMovementKeys(self, cmdlist):
        x=0; y=0; z=0
        playing = self.hero.avatar.curAnimation.name
        for cls, cmd, arg in cmdlist:
            if arg == BUTTONUP:
                self.input_changed = True
                if cmd == P1_DOWN:
                    if playing == "crouch":
                        self.hero.avatar.play("uncrouch", loop=0)

                elif cmd == P1_LEFT or cmd == P1_RIGHT:
                    if self.hero_body.vel.z == 0:
                        y = 0
                    else:
                        self.wants_to_stop_on_landing = True

                elif cmd == P1_ACTION3 and self.hero.held:
                    self.hero.parent.unjoin(hero_body, self.hero.held)
                    msg = self.text['ungrab'].format(self.hero.held.parent.name)
                    self.hero.parent.emitText(msg, thing=self.hero)
                    self.hero.held = None

            # these actions will repeat as button is held down
            elif arg == BUTTONDOWN or arg == BUTTONHELD:
                self.input_changed = True
                if cmd == P1_UP:
                    self.elevatorUp()

                elif cmd == P1_DOWN:
                    if not self.elevatorDown():
                        if self.area.grounded(self.area.getBody(self.hero)):
                            if playing == "stand":
                                self.hero.avatar.play("crouch", loop_frame=4)

                if cmd == P1_LEFT:
                    y = -1
                    self.hero.avatar.flip = 1

                elif cmd == P1_RIGHT:
                    y = 1
                    self.hero.avatar.flip = 0


            # these actions will not repeat if button is held
            if arg == BUTTONDOWN:
                self.input_changed = True
                if cmd == P1_ACTION1:
                    for thing, body in getNearby(self.hero, 8):
                        if hasattr(thing, "use"):
                            thing.use(self.hero)

                elif cmd == P1_ACTION2:
                    self.handle_jump()

                elif cmd == P1_ACTION3:
                    for thing, body in getNearby(self.hero, 6):
                        if thing.pushable and not self.hero.held:
                            self.hero.parent.join(hero_body, body)
                            self.hero.held = body
                            msg = self.text['grab'].format(thing.name) 
                            self.hero.parent.emitText(msg, thing=self.hero)


        if (not x == 0) or (not y == 0) or (not z == 0):
            if self.hero.held:
                y = y / 3.0

        self.player_vector = x, y*self.hero.move_speed, z


    def handle_jump(self):
        """
        assume that the key was pressed and the player wants to jump
        """

        playing = self.hero.avatar.curAnimation.name

        if self.hero_body.vel.z == 0:
            self.jumps = 1
            if (not self.hero.held) and (not playing == "crouch"):
                self.hero_body.vel.z = -self.hero.jump_strength
                self.hero_body.acc.z = 0.0
        else:
            # double jump
            if self.jumps <= 1:
                self.jumps += 2
                self.hero_body.vel.z = -self.hero.jump_strength
                self.hero_body.acc.z = 0.0

