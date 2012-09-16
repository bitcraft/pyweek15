from lib2d import res, quadtree, vec, context, bbox
from lib2d.utils import *

import euclid, physicsbody
import pygame, itertools



class PlatformerMixin(object):
    """
    Mixin class that contains methods to translate world coordinates to screen
    or surface coordinates.
    """

    # accessing the bbox by index much faster than accessing by attribute
    def toRect(self, bbox):
        return pygame.Rect((bbox[1], bbox[2], bbox[4], bbox[5]))


    def rectToBody(self, rect):
        newbbox = (0, rect.x, rect.y, 1, rect.width, rect.height)
        return physicsbody.Body3(newbbox, (0,0,0), (0,0,0), 0)



class AdventureMixin(object):
    """
    Mixin class that contains methods to translate world coordinates to screen
    or surface coordinates.
    """

    # accessing the bbox by index much faster than accessing by attribute
    def toRect(self, bbox):
        return pygame.Rect((bbox[0], bbox[1], bbox[3], bbox[4]))


    def rectToBody(self, rect):
        newbbox = (rect.x, rect.y, 0, rect.width, rect.height, 0)
        return physicsbody.Body3(newbbox, (0,0,0), (0,0,0), 0)


class PhysicsGroup(context.Context):
    """
    object mangages a list of physics bodies and moves them around to simulate
    simple physics.  Currently, only gravity and simple movement is implemented
    without friction or collision handling.

    static bodies are simply called 'geometry' and handled slightly different
    from dynamic bodies.

    the dimensions of your objects are important!  internally, collision
    detection against static bodies is handled by pygame rects, which cannot
    handle floats.  this means that the smallest body in the game must be at
    least a 1x1x1 meter cube.

    For speed, only 2 axises are checked for collisions:
        using the adventure mixin, this will be the xy plane
        using the platformer mixin, this will be the zy plane
        the bboxes passed to geometry will be translated into the correct type

    a word on the coordinate system:
        coordinates are 'right handed'
        x axis moves toward viewer
        y axis move left right
        z axis is height

    """

    def __init__(self, scaling, timestep, gravity, bodies, geometry, precision=2):
        self.scaling = scaling
        self.gravity = euclid.Vector3(0,0,gravity)
        self.bodies = bodies
        self.precision = precision
        self.sleeping = []
        self.staticBodies = []
        [ self.scaleBody(b, scaling) for b in self.bodies ]

        rects = []
        for bbox in geometry:
            body = physicsbody.Body3(bbox, (0,0,0), (0,0,0), 0)
            self.scaleBody(body, scaling)
            self.staticBodies.append(body)
            rects.append(self.toRect(body.bbox))

        self.geometry = quadtree.FastQuadTree(rects)

        self.setTimestep(timestep)


    def __iter__(self):
        return itertools.chain(self.bodies, self.staticBodies)


    def update(self, time):
        for body in (b for b in self.bodies if b not in self.sleeping):
            body.acc += self.gravity_delta
            body.vel += body.acc * self.timestep
            x, y, z = body.vel

            if not x==0:
                if not self.moveBody(body, (x, 0, 0)):
                    if abs(body.vel.x) > .2:
                        body.acc.x = 0.0
                        body.vel.x = -body.vel.x * .2
                    else:
                        body.acc.x = 0.0
                        body.vel.x = 0.0

            if not y==0:
                if not self.moveBody(body, (0, y, 0)):
                    if abs(body.vel.y) > .2:
                        body.acc.y = 0.0
                        body.vel.y = -body.vel.y * .2
                    else:
                        body.acc.y = 0.0
                        body.vel.y = 0.0

            if z > 0:
                if not self.moveBody(body, (0, 0, z)):
                    if abs(body.vel.z) > 2.5:
                        body.acc.z = 0.0
                        body.vel.z = -body.vel.z * .2
                    else:
                        body.acc.z = 0.0
                        body.vel.z = 0.0
 
            elif z < 0:
                self.moveBody(body, (0, 0, z))

            if body.bbox.z == 0:
                body.vel.x = body.vel.x * self.ground_friction
                body.vel.y = body.vel.y * self.ground_friction

            if (round(body.vel.x, 4) ==
                round(body.vel.y, 4) ==
                round(body.vel.z, 1) == 0.0) and body.bbox.z == 0:
                self.sleeping.append(body)


    def scaleBody(self, body, scale):
        body.bbox.scale(scale, scale, scale)


    def dynamicBodies(self):
        return iter(self.bodies)


    def wakeBody(self, body):
        try:
            self.sleeping.remove(body)
        except:
            pass

    
    def setTimestep(self, time):
        self.timestep = time
        self.gravity_delta = self.gravity * time
        self.ground_friction = pow(.0001, self.timestep)


    def moveBody(self, body, (x, y, z), clip=True):
        body.bbox.move(x, y, z)

        # test for collision with level geometry
        if self.testCollision(body.bbox):
            if body.bbox[2] < -10:
                body.bbox[2] = -10.0
                body.bbox.move(-x, -y, 0)
            else:
                body.bbox.move(-x, -y, -z)
            return False

        else:
            # test for collision with another object
            # must do a spatial hash or oct tree or something here [later]
            bbox = body.bbox
            for other in (b for b in self.bodies if b is not body):
                if bbox.collidebbox(other.bbox):
                    if self.moveBody(other, (x, y, z)):
                        return True
                    else:
                        body.bbox.move(-x, -y, -z)
                        return False

        return True


    def testCollisionOther(self, body, bbox=None):
        if bbox is None:
            bbox = body.bbox
        for other in (b for b in self.bodies if b is not body):
            if bbox.collidebbox(other.bbox):
                return True
        return False



    def testCollision(self, bbox):
        # for adventure games
        if bbox[2] < 0:
            return True
        return bool(self.geometry.hit(self.toRect(bbox)))


class PlatformerPhysicsGroup(PhysicsGroup, PlatformerMixin):
    pass


class AdventurePhysicsGroup(PhysicsGroup, AdventureMixin):
    pass
