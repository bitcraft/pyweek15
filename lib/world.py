from lib2d.area import AbstractArea
from lib2d.buildarea import fromTMX
from lib2d.avatar import Avatar
from lib2d.animation import Animation, StaticAnimation
from lib2d.objects import AvatarObject
from lib2d.image import Image
from lib.level import Level
from lib.entity import Entity
from lib2d import res


def build():

    # build the initial environment
    uni = AbstractArea()
    uni.name = 'universe'
    uni.setGUID(0)


    # some characters
    avatar = Avatar([
        StaticAnimation(
            Image('astro0-helmet-stand.png', colorkey=True),
            'stand'),
        Animation(
            Image('astro0-helmet-walk.png', colorkey=True),
            'walk',
            range(14), 1, 50),
    ])

    npc = Entity(
        avatar,
        [],
        Image('face0.png')
    )

    npc.setName("Brahbrah")
    npc.setGUID(1)
    npc.size = (16,16,32)
    npc.move_speed = .20
    uni.add(npc)


    # levels
    level = fromTMX(uni, "level1.tmx")
    level.setName("Level 1")
    level.setGUID(5001)

    #level = Area()
    #level.setGUID(5001)
    #uni.add(level)

    return uni
