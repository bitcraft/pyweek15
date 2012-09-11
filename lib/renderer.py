from lib2d.tilemap import BufferedTilemapRenderer
from lib2d.objects import AvatarObject, GameObject
from lib2d.bbox import BBox
from lib2d.ui import Element
from lib2d import vec

from pygame import Rect, draw, Surface
import weakref


DEBUG = 0


def screenSorter(a):
    return a[-1].x


class AvatarLayer(GameObject):
    def __init__(self, area, extent):
        self.area = area


class LevelCamera(Element):
    """
    The level camera manages sprites on the screen and a tilemap renderer.
    it will be mangled some to use the 3d coordinate system of the engine
    """

    name = 'LevelCamera'

    def __init__(self, parent, area, extent):
        Element.__init__(self, parent)

        self.area = area
        self.set_extent(extent)

        w, h = self.extent.size

        # create a renderer for the map
        self.maprender = BufferedTilemapRenderer(area.tmxdata, (w, h))
        #self.maprender.center((w/2, h/2))

        self.map_height = area.tmxdata.tilewidth * area.tmxdata.width
        self.map_width = area.tmxdata.tileheight * area.tmxdata.height
        self.blank = True

        self.ao = self.refreshAvatarObjects()

        # parallax hack below
        import pytmx, lib2d.res

        par_tmx = pytmx.tmxloader.load_pygame(
                  lib2d.res.mapPath('parallax0.tmx'), force_colorkey=(128,128,0))

        # EPIC HACK GO
        i = lib2d.res.loadImage("../tilesets/level0.png")
        colorkey = i.get_at((0,0))[:3]
        self.maprender.buffer.set_colorkey(colorkey)
        self.parallaxrender = BufferedTilemapRenderer(par_tmx, (w, h))
 

    def refreshAvatarObjects(self):
        return [ i for i in self.area.bodies.keys() if hasattr(i, "avatar")]


    # HACK
    def getAvatarObjects(self):
        if self.area.changedAvatars:
            self.area.changedAvatars = False
            self.ao = self.refreshAvatarObjects()
        return self.ao


    def set_extent(self, extent):
        """
        the camera caches some values related to the extent, so it becomes
        nessessary to call this instead of setting the extent directly.
        """

        # our game world swaps the x and y axis, so we translate it here
        #x, y, w, h = extent
        #self.extent = Rect(y, x, h, w)
        self.extent = Rect(extent)

        self.half_width = self.extent.width / 2
        self.half_height = self.extent.height / 2
        self.width  = self.extent.width
        self.height = self.extent.height
        self.zoom = 1.0


    def center(self, (x, y, z)):
        """
        center the camera on a world location.
        """

        x, y = self.area.worldToPixel((x, y, z))

        if self.map_height >= self.height:
            if y <= self.half_height:
                y = self.half_height

            elif y > self.map_height - self.half_height- 1:
                y = self.map_height - self.half_height - 1 
        else:
            y = self.map_height / 2

        if self.map_width >= self.width:
            if x <= self.half_width:
                x = self.half_width

            elif x > self.map_width - self.half_width - 1:
                x = self.map_width - self.half_width - 1

        else:
            x = self.map_width / 2

        self.extent.center = (x, y)
        self.maprender.center((x, y))

        self.parallaxrender.center((x/2.0, y/2.0))


    def clear(self, surface):
        raise NotImplementedError


    def draw(self, surface, rect):
        onScreen = []

        avatarobjects = self.refreshAvatarObjects()

        if self.blank:
            self.blank = False
            self.maprender.blank = True

        # quadtree collision testing would be good here
        for a in avatarobjects:
            bbox = self.area.getBBox(a)
            x, y, z, d, w, h = bbox
            x, y = self.area.worldToPixel((x, y, z))
            x -= self.extent.left
            y -= self.extent.top
            onScreen.append((a.avatar.image, Rect((x, y), (w, h)), 1, a, bbox))

        # should not be sorted every frame
        onScreen.sort(key=screenSorter)

        # mor HAX
        #import pygame
        #w, h = surface.get_size()
        #temp = Surface((w*1.5, h))
        #self.parallaxrender.draw(temp, Rect(0,0,w*1.5,h*1.5), [])
        #temp = pygame.transform.scale(temp, (w,h))
        #surface.blit(temp, (0,0))

        self.parallaxrender.draw(surface, rect, [])
        dirty = self.maprender.draw(surface, rect, onScreen)

        if DEBUG:
            for bbox in self.area.rawGeometry:
                x, y, z, d, w, h = bbox
                y -= self.extent.left
                z -= self.extent.top
                draw.rect(surface, (255,100,100), (y, z, w, h))

            for i in onScreen:
                draw.rect(surface, (100,255,100), i[1])


        return dirty


    def worldToSurface(self, (x, y, z)):
        """
        Translate world coordinates to coordinates on the surface
        underlying area is based on 'right handed' 3d coordinate system
        xy is horizontal plane, with x pointing toward observer
        z is the vertical plane
        """

        xx, yy = self.area.worldToPixel((x, y, z))
        return xx - self.extent.left, yy - self.extent.top

    def surfaceToWorld(self, (x, y)):
        """
        Transform surface coordinates to coordinates in the world
        surface coordinates take into account the camera's extent
        """

        return self.area.pixelToWorld((x+self.extent.top,y+self.extent.left))
