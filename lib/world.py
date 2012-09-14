from lib2d.area import AbstractArea
from lib2d.buildarea import fromTMX
from lib2d.avatar import Avatar
from lib2d.animation import Animation, StaticAnimation
from lib2d.objects import AvatarObject
from lib2d.image import Image
from lib.level import Level
from lib.entity import Entity
from lib2d import res

from items import *


def build():

    # build the initial environment
    uni = AbstractArea()
    uni.name = 'universe'
    uni.setGUID(0)

    # =========================================================================
    # our charming hero

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
    npc.move_speed = .5   #.025
    npc.jump_strength = .5
    uni.add(npc)


    # =========================================================================
    # some keys

    # red
    #avatar = Avatar([
    #    StaticAnimation(
    #        Image('red-key.png', colorkey=True),
    #        'stand')
    #])

    avatar = Avatar([
        Animation(
            Image('red-key-spinning.png', colorkey=True),
            'stand',
            range(12), 1, 100)
    ])

    red_key = Key(avatar)
    red_key.setName('Red Key')
    red_key.setGUID(513)
    uni.add(red_key)


    # green
    avatar = Avatar([
        StaticAnimation(
            Image('green-key.png', colorkey=True),
            'stand')
    ])

    green_key = Key(avatar)
    green_key.setName('Green Key')
    green_key.setGUID(514)
    uni.add(green_key)


    # blue
    avatar = Avatar([
        StaticAnimation(
            Image('blue-key.png', colorkey=True),
            'stand')
    ])

    blue_key = Key(avatar)
    blue_key.setName('Blue Key')
    blue_key.setGUID(515)
    uni.add(blue_key)


    # =========================================================================
    # levels
    level = fromTMX(uni, "level2.tmx")
    level.setName("Level 1")
    level.setGUID(5001)

    #level = Area()
    #level.setGUID(5001)
    #uni.add(level)

    return uni
