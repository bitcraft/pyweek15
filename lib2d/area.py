import res
from pathfinding.astar import Node
from objects import GameObject
from quadtree import QuadTree, FrozenRect
from pygame import Rect
from bbox import BBox
from pathfinding import astar
from lib2d.signals import *
from vec import Vec2d, Vec3d
import physics
import math

cardinalDirs = {"north": math.pi*1.5, "east": 0.0, "south": math.pi/2, "west": math.pi}



class PathfindingSentinel(object):
    """
    this object watches a body move and will adjust the movement as needed
    used to move a body when a path is set for it to move towards
    """

    def __init__(self, body, path):
        self.body = body
        self.path = path
        self.dx = 0
        self.dy = 0

    def update(self, time):
        if worldToTile(bbox.origin) == self.path[-1]:
            pos = path.pop()
            theta = math.atan2(self.destination[1], self.destination[0])
            self.destination = self.position + self.destination
            self.dx = self.speed * cos(theta)
            self.dy = self.speed * sin(theta) 

        self.area.movePosition(self.body, (seldf.dx, self.dy, 0))


class CollisionError(Exception):
    pass


class ExitTile(FrozenRect):
    def __init__(self, rect, exit):
        FrozenRect.__init__(self, rect)
        self._value = exit

    def __repr__(self):
        return "<ExitTile ({}, {}, {}, {}): {}>".format(
            self._left,
            self._top,
            self._width,
            self._height,
            self._value)





class AbstractArea(GameObject):
    pass


class Sound(object):
    """
    Class that manages how sounds are played and emitted from the area
    """

    def __init__(self, filename, ttl):
        self.filename = filename
        self.ttl = ttl
        self._done = 0
        self.timer = 0

    def update(self, time):
        if self.timer >= self.ttl:
            self._done = 1
        else:
            self.timer += time

    @property
    def done(self):
        return self._done



class AdventureMixin(object):
    """
    Mixin class that contains methods to translate world coordinates to screen
    or surface coordinates.
    The methods will translate coordinates of the tiled map

    TODO: manipulate the tmx loader to swap the axis
    """

    def tileToWorld(self, (x, y, z)):
        xx = int(x) * self.tmxdata.tileheight
        yy = int(y) * self.tmxdata.tilewidth
        return xx, yy, z


    def pixelToWorld(self, (x, y)):
        return Vec3d(y, x, 0)


    def toRect(self, bbox):
        # return a rect that represents the object on the xy plane
        # currently this is used for geometry collision detection
        return Rect((bbox.x, bbox.y, bbox.depth, bbox.width))


    def worldToPixel(self, (x, y, z)):
        return Vec2d((y, x))


    def worldToTile(self, (x, y, z)):
        xx = int(x) / self.tmxdata.tilewidth
        yy = int(y) / self.tmxdata.tileheight
        zz = 0
        return xx, yy, zz


    def setForce(self, body, (x, y, z)):
        body.acc = Vec2d(x, y)


class PlatformMixin(object):
    """
    Mixin class is suitable for platformer games
    """

    physicsGroupClass = physics.PlatformerPhysicsGroup

    def toRect(self, bbox):
        # return a rect that represents the object on the zy plane
        return Rect((bbox.y, bbox.z+bbox.height, bbox.width, bbox.height))


    """
    the underlying physics 'engine' is only capable of calculating 2 axises.
    for playformer type games, we use the zy plane for calculations
    """

    def grounded(self, body):
        try:
            return self._grounded[body]
        except:
            return False


    def applyForce(self, body, (x, y, z)):
        body.acc += Vec2d(y, z)


    def worldToPixel(self, (x, y, z)):
        return (y*self.scaling, z*self.scaling)


    def worldToTile(self, (x, y, z)):
        xx = int(x) / self.tmxdata.tilewidth
        yy = int(y) / self.tmxdata.tileheight
        zz = 0
        return xx, yy, zz



class PlatformArea(AbstractArea, PlatformMixin):
    """3D environment for things to live in.
    Includes basic pathfinding, collision detection, among other things.

    Uses a quadtree for fast collision testing with level geometry.

    Bodies can exits in layers, just like maps.  since the y values can
    vary, when testing for collisions the y value will be truncated and tested
    against the quadtree that is closest.  if there is no quadtree, no
    collision testing will be done.

    There are a few hacks to be aware of:
        bodies move in 3d space, but level geometry is 2d space
        when using pygame rects, the y value maps to the z value in the area

    a word on the coordinate system:
        coordinates are 'right handed'
        x axis moves toward viewer
        y axis move left right
        z axis is height

    Expects to load a specially formatted TMX map created with Tiled.
    Layers:
        Control Tiles
        Upper Partial Tiles
        Lower Partial Tiles
        Lower Full Tiles

    Contains a very basic discrete collision system.

    The control layer is where objects and boundries are placed.  It will not
    be rendered.  Your map must not have any spaces that are open.  Each space
    must have a tile in it.  Blank spaces will not be rendered properly and
    will leave annoying trails on the screen.

    The control layer must be created with the utility included with lib2d.  It
    contains metadata that lib2d can use to layout and position objects
    correctly.

    REWRITE: FUNCTIONS HERE SHOULD NOT CHANGE STATE

    NOTE: some of the code is specific for maps from the tmxloader
    """

    # real mars gravity is 3.69 m/s2
    gravity = 3.69


    def defaultPosition(self):
        return BBox((0,0,0,1,1,1))

    def defaultSize(self):
        # TODO: this cannot be hardcoded!
        return (10, 8)


    def __init__(self):
        AbstractArea.__init__(self)
        self.exits    = {}
        self.geometry = {}       # geometry (for collisions) of each layer
        self.extent = None       # absolute boundries of the area
        self.messages = []
        self.time = 0
        self.tmxdata = None
        self.mappath = None
        self.sounds = []
        self.soundFiles = []
        self.inUpdate = False
        self._addQueue = []
        self._removeQueue = []
        self._addQueue = []
        self.drawables = []      # HAAAAKCCCCKCK
        self.changedAvatars = True #hack
        self.music_pos = 0

        self.flashes = []
        self.inUpdate = False
        self._removeQueue = []

        # internal physics stuff
        self.rawGeometry = []    # a list of bbox objects
        self.bodies = {}
        self.physicsgroup = None
        # BUG: scaling doesn't work properly since pygame rects only store ints
        self.scaling = 1.0 # MUST BE FLOAT (how many pixels are in a meter?)


    def load(self):
        import pytmx

        self.tmxdata = pytmx.tmxloader.load_pygame(
                       self.mappath, force_colorkey=(128,128,0))

        return 

        # quadtree for handling collisions with exit tiles
        rects = []
        for guid, param in self.exits.items():
            try:
                x, y, l = param[0]
            except:
                continue

            rects.append(ExitTile((x,y,
                self.tmxdata.tilewidth, self.tmxdata.tileheight), guid))

        # get sounds from tiles
        for i, layer in enumerate(self.tmxdata.tilelayers):
            props = self.tmxdata.getTilePropertiesByLayer(i)
            for gid, tileProp in props:
                for key, value in tileProp.items():
                    if key[4:].lower() == "sound":
                        self.soundFiles.append(value)

        # get sounds from objects
        for i in [ i for i in self.getChildren() if i.sounds ]:
            self.soundFiles.extend(i.sounds)

        #self.exitQT = QuadTree(rects)


    def add(self, thing, pos=None):
        AbstractArea.add(self, thing)

        if pos is None:
            pos = self.defaultPosition().origin

        # hackish stuff to allow the BBox class to properly subclass built-in
        # list class (improves speed when translating bboxes)
        l = list(pos)
        l.extend(thing.size)
        body = physics.Body3(BBox(l), (0,0,0), (0,0,0), 0)
        self.bodies[thing] = body

        # physics groups cannot be modified once created.  just make a new one.
        # physics 'engine' is tuned for 200 fps (read below):
        #   5 updates per draw
        #   40 draws per second
        #   total 200 fps
        #   1/200 = 0.005
        # scaling is needed because by default 1 pixel is one meter
        # we slow down the physics just a bit to make it more playable
        bodies = self.bodies.values()
        self.physicsgroup = self.physicsGroupClass(1.0/self.scaling,
                                                   0.005,
                                                   self.gravity,
                                                   bodies,
                                                   self.rawGeometry)

        self.changedAvatars = True


    def remove(self, thing):
        if self.inUpdate:
            self._removeQueue.append(thing)
            return

        AbstractArea.remove(self, thing)
        del self.bodies[thing]
        self.changedAvatars = True

        # hack
        try:
            self.drawables.remove(thing)
        except (ValueError, IndexError):
            pass


    def movePosition(self, body, (x, y, z), push=True, caller=None, \
                     suppress_warp=False, clip=True):

        return

        self._sendBodyMove(body, caller=caller)

        bbox2 = newbbox.move(0,0,32)
        tilePos = self.worldToTile(bbox2.topcenter)
        try:
            # emit sounds from bodies walking on them
            prop = self.tmxdata.getTileProperties(tilePos)
        except:
            pass

        else:
            if prop is not None:
                name = prop.get('walkSound', False)
                if name:
                    self.emitSound(name, newbbox.bottomcenter, ttl=600)

        try:
            # test for collisions with exits
            exits = self.exitQT.hit(self.toRect(newbbox))
        except AttributeError:
            exits = []


        if exits and not suppress_warp:
            # warp the player
            exit = exits.pop()

            # get the position and guid of the exit tile of the other map
            fromExit, guid = self.exits[exit.value]
            if guid is not None: 
                # used to correctly align sprites
                fromTileBBox = BBox(fromExit, (16,16,1))
                tx, ty, tz = fromTileBBox.origin
            
                # get the GUID of the map we are warping to
                dest = self.getRoot().getChildByGUID(guid)
                toExit, otherExit = dest.exits[exit.value]

                bx, by, bz = newbbox.origin
                ox, oy, oz = originalbbox.origin
                bz = 0

                # determine wich direction we are traveling through the exit
                angle = math.atan2(oy-by, ox-bx)

                # get the position of the tile in out new area
                newx, newy, newz = toExit

                # create a a bbox to position the object in the new area
                dx = 16 / 2 - newbbox.depth / 2
                dy = 16 / 2 - newbbox.width / 2
                dz = 0

                exitbbox = BBox((newx+dx, newy+dy, newz+dz), newbbox.size)
                face = self.getOrientation(body)
                dest.add(body)
                dest.setBBox(body, exitbbox)
                dest.setOrientation(body, face)
                
                # when changing the destination, we do a bunch of moves first
                # to push objects out of the way from the door...if possible
                dx = round(math.cos(angle))
                dy = round(math.sin(angle))
                dz = 0
                dest.movePosition(body, (dx*20, dy*20, dz*20), False, \
                                  suppress_warp=True, clip=False)

                for x in range(40):
                    dest.movePosition(body, (-dx, -dy, -dz), True, \
                                      suppress_warp=True, clip=False)

                # send a signal that this body is warping
                bodyWarp.send(sender=self, body=body, destination=dest,
                              caller=caller)

        return True 


    def getBody(self, thing):
        return self.bodies[thing]


    def setOrientation(self, thing, angle):
        """ Set the angle the object is facing.  Expects radians. """

        if isinstance(angle, str):
            try:
                angle = cardinalDirs[angle]
            except:
                raise

        self.getBody(thing).o = angle


    def setLayerGeometry(self, layer, rects):
        """
        set the layer's geometry.  expects a list of rects.
        """

        import quadtree

        self.geometry[layer] = rects


    def pathfind(self, start, destination):
        """Pathfinding for the world.  Destinations are 'snapped' to tiles.
        """

        def NodeFactory(pos):
            x, y = pos[:2]
            l = 0
            return Node((x, y))

            try:
                if self.tmxdata.getTileGID(x, y, l) == 0:
                    node = Node((x, y))
                else:
                    return None
            except:
                return None
            else:
                return node

        start = self.worldToTile(start)
        destination = self.worldToTile(destination)
        path = astar.search(start, destination, NodeFactory)
        return path


    def emitText(self, text, pos=None, thing=None):
        if pos==thing==None:
            raise ValueError, "emitText requires a position or thing"

        if thing:
            pos = self.bodies[thing].bbox.center
        emitText.send(sender=self, text=text, position=pos)
        self.messages.append(text)


    def emitSound(self, filename, pos=None, thing=None, ttl=350):
        if pos==thing==None:
            raise ValueError, "emitSound requires a position or thing"

        self.sounds = [ s for s in self.sounds if not s.done ]
        if filename not in [ s.filename for s in self.sounds ]:
            if thing:
                pos = self.bodies[thing].bbox.center
            emitSound.send(sender=self, filename=filename, position=pos)
            self.sounds.append(Sound(filename, ttl))


    def update(self, time):
        self.inUpdate = True
        self.time += time

        [ sound.update(time) for sound in self.sounds ]

        for thing in self.bodies.keys():
            thing.avatar.update(time)

        self.physicsgroup.update(time)

        # awkward looping allowing objects to be added/removed during update
        self.inUpdate = False
        [ self.add(thing) for thing in self._addQueue ] 
        self._addQueue = []
        [ self.remove(thing) for thing in self._removeQueue ] 
        self._removeQueue = []


    def setExtent(self, rect):
        self.extent = Rect(rect)


    def getPositions(self):
        return [ (o, b.origin) for (o, b) in self.bboxes.items() ]


    def getOldPosition(self, body):
        return self._oldbboxes[body]


    def _sendBodyMove(self, body, caller, force=None):
        position = body.bbox.origin
        bodyAbsMove.send(sender=self, body=body, position=position, caller=caller, force=force)

    
    def warpBody(self):
        """
        move a body to another area using an exit tile.
        objects on or around the tile will be push out of the way
        if objects cannot be pushed, then the warp will fail
        """
        pass



    #  CLIENT API  --------------


    def join(self, body0, body1):
        self.joins.append((body0, body1))


    def unjoin(self, body0, body1):
        self.joins.remove((body0, body1))


    def getRect(self, thing):
        return self.toRect(self.bodies[thing].bbox)


    def isGrounded(self, thing):
        return self.grounded(self.bodies[thing])


    def getBBox(self, thing):
        return self.bodies[thing].bbox


    def setBBox(self, thing, bbox):
        """ Attempt to set a bodies bbox.  Returns True if able. """

        if not isinstance(bbox, BBox):
            bbox = BBox(bbox)

        body = self.getBody(thing)
        body.oldbbox = body.bbox
        body.bbox = bbox


    def getOrientation(self, thing):
        """ Return the angle thing is facing in radians """
        return self.bodies[thing].o


    def setPosition(self, thing, origin):
        body = self.bodies[thing]
        body.bbox = BBox(origin, body.bbox.size)


    def getSize(self, thing):
        """ Return 3d size of the object """
        return self.bodies[thing].bbox.size


    def getPosition(self, thing):
        """ for clients to find position in world of things, not bodies """
        return self.bodies[thing].bbox.origin


    def getBody(self, thing):
        return self.bodies[thing]


    def stick(self, body):
        pass


    def unstick(self, body):
        pass
