"""
lootr by Dr. Jekyll
Beta

Big thanks to TheChingrish for cross checking the mods on the items, and to
yosuki for the original item guide.

Description: picks up the loot you want, and only that.
- LOOTR button in the Esc menu opens the Lootr window. Pick a Class, Slot and Item,
  then mark its mods in the table: one column per number of mods (Stock, Modified,
  Custom, Experimental, Prototype), one row per mod it can roll ("x2" rows for mods
  that can roll twice).
- cells: left click cycles -- (any), check (want), X (don't want); right click puts
  it back to --. An item is wanted when it has every checked mod in its column and
  no X mod.
- column names: left click cycles ANY (green: any item with that many mods, except
  ones with an X mod), NONE (red: none of them) and back; right click puts it back.
  Your marks are kept underneath. Stock has no cells: ANY Stock picks up stock ones.
- Settings (in the Lootr window):
    Auto Loot                     presses interact on wanted loot you stand on
    Message On Pickup             "+ item" floats up when it is picked up
    Highlight Items               green box around wanted loot on the ground
    Magnify Items                 enlarged copy above wanted loot on the ground
    Highlight Items In Inventory  the same box in the inventory, stash and HUD
    Show Chest Contents (BETA)    wanted items (and HP when you are hurt) shown
                                  above chests before they are opened
- items you drop yourself are never auto looted; they get a yellow box instead.
- a red "Inventory Full" shows when the backpack is full (at most every 5 s).
- Reset To Defaults asks first, then clears every setting and every mark.
- other plugins' drawing is hidden while the Lootr window is open.

Your marks and settings are saved in lootr_settings.json in the SBPE folder.

Install: drop this file into SBPE's plugins folder.

If you want to customize it paste this into config.ini:

[plugin_lootr]
enabled = yes
# text of the Esc menu button
label = Lootr
# your in-game interact key (SDL key name), pressed by Auto Loot
interact_key = A
"""
import json
import logging
import os
import struct
import time
import weakref

from _remote import ffi, lib
from manager import PluginBase
import util


STAT_NAMES = {
    1: 'HP',
    2: 'Max HP',
    3: 'Ammo',
    4: 'Max Ammo',
    8: 'Air Jumps',
    9: 'Damage (flat)',
    10: 'Armor',
    11: 'Movement Speed',
    12: 'Jump Height',
    13: 'Range',
    14: 'Precise',
    16: 'EC',
    17: 'Implant Slot',
    18: 'Damage %',
    19: 'Base Crit Chance',
    20: 'Crit Damage',
    21: 'Air Dashes',
    22: 'Knockback Resist',
    23: 'Crit Chance',
    24: 'Item Crit Chance',
    25: 'Item Crit Damage',
    26: 'UC',
    27: 'Ammo Multiplier',
    32: 'Penetrating',
    33: 'Bounce',
    34: 'Explosive',
    35: 'Incendiary',
    36: 'Subobjects/Shots',
    37: 'Speed %',
    38: 'Lifetime (ms)',
    39: 'Seeking',
    41: 'Radius',
    42: 'Acceleration',
    43: 'Armor Pierce',
    44: 'Key',
    45: 'Simultaneous',
    46: 'Secondary Subobjects',
    47: 'Barbed',
    48: 'Trisected',
    49: 'Gravity %',
    50: 'Leech',
    51: 'Extra Hit',
    52: 'Reflect',
    53: 'Move Time (ms)',
    54: 'Item Armor',
    55: 'Quick Shot / Anim Speed',
    56: 'Shielded',
    57: 'Cooldown',
    60: 'Imagemap',
}

SLOT_NAMES = {
    256: 'Main',
    512: 'Secondary',
    768: 'Special',
    1024: 'Armor',
    1280: 'Mobility',
    1536: 'Implant',
    None: 'Pickup',
}

CHAR_NAMES = {
    1: 'Wildfire',
    2: 'Duskwing',
    3: 'Ironclad',
    5: 'Fabricator',
}

ITEMS = {
    #
    #   MAIN
    #

    31: dict(name='Kantikoy Repeater', slot=256, tier=1, itemclass=3, usableby=[1], family='repeater',
         base=[], mods={13: 100, 14: 100, 32: 0, 33: 1, 34: 0, 36: 1, 43: 100}, seen={32: [0], 33: [1], 34: [0], 36: [1]}, doubles=[33, 36], source='guide+observed+server'),
         # Range, Precise, Penetrating, Bounce, Explosive, Subobjects/Shots, Armor Pierce; can roll twice: Bounce, Subobjects/Shots
    147: dict(name='Compound Repeater', slot=256, tier=2, itemclass=3, usableby=[1], family='repeater',
         base=[], mods={13: 100, 14: 100, 32: 0, 33: 1, 34: 0, 36: 1, 43: 100}, seen={13: [100], 33: [1], 36: [1], 43: [100]}, doubles=[33, 36], source='guide+observed'),
         # Range, Precise, Penetrating, Bounce, Explosive, Subobjects/Shots, Armor Pierce; can roll twice: Bounce, Subobjects/Shots
    148: dict(name='Redshift Repeater', slot=256, tier=3, itemclass=3, usableby=[1], family='repeater',
         base=[], mods={13: 100, 14: 100, 32: 0, 33: 1, 34: 0, 36: 1, 43: 100}, seen={13: [100], 36: [1]}, doubles=[33, 36], source='guide+server'),
         # Range, Precise, Penetrating, Bounce, Explosive, Subobjects/Shots, Armor Pierce; can roll twice: Bounce, Subobjects/Shots
    149: dict(name='Tektite Repeater', slot=256, tier=4, itemclass=3, usableby=[1], family='repeater',
         base=[], mods={13: 100, 14: 100, 32: 0, 33: 1, 34: 0, 36: 1, 43: 100}, seen={32: [0], 36: [1]}, doubles=[33, 36], source='guide+observed+server'),
         # Range, Precise, Penetrating, Bounce, Explosive, Subobjects/Shots, Armor Pierce; can roll twice: Bounce, Subobjects/Shots
    207: dict(name='Aerolith Repeater', slot=256, tier=5, itemclass=3, usableby=[1], family='repeater',
         base=[], mods={13: 100, 14: 100, 32: 0, 33: 1, 34: 0, 36: 1, 43: 100}, seen={33: [1], 36: [1], 43: [100]}, doubles=[33, 36], source='guide+observed'),
         # Range, Precise, Penetrating, Bounce, Explosive, Subobjects/Shots, Armor Pierce; can roll twice: Bounce, Subobjects/Shots

    4: dict(name='Shotgun', slot=256, tier=0, itemclass=3, usableby=[1], family=None,
         base=[], mods={}, seen={}, source='none'),
         # no mods
    5: dict(name='Arblast', slot=256, tier=1, itemclass=3, usableby=[1], family='shotgun',
         base=[], mods={13: 70, 32: 0, 33: 1, 34: 0, 36: 2, 43: 100, 55: 20}, seen={34: [0], 36: [2]}, source='shotgun-family+server'),
         # Range, Penetrating, Bounce, Explosive, Subobjects/Shots, Armor Pierce, Quick Shot / Anim Speed
    150: dict(name='Dragoon', slot=256, tier=3, itemclass=3, usableby=[1], family='shotgun',
         base=[], mods={13: 70, 32: 0, 33: 1, 34: 0, 36: 3, 43: 100, 55: 20}, seen={33: [1], 36: [3]}, source='shotgun-family+server'),
         # Range, Penetrating, Bounce, Explosive, Subobjects/Shots, Armor Pierce, Quick Shot / Anim Speed
    208: dict(name='Bombard', slot=256, tier=5, itemclass=3, usableby=[1], family='shotgun',
         base=[], mods={13: 70, 32: 0, 33: 1, 34: 0, 36: 4, 43: 100, 55: 20}, seen={33: [1], 36: [4], 43: [100], 55: [25]}, source='guide+observed'),
         # Range, Penetrating, Bounce, Explosive, Subobjects/Shots, Armor Pierce, Quick Shot / Anim Speed

    209: dict(name='Jansky Repeater', slot=256, tier=1, itemclass=3, usableby=[1], family='soidal',
         base=[], mods={13: 125, 14: 100, 32: 0, 34: 0, 36: 1, 43: 100}, seen={13: [125], 14: [100], 34: [0], 36: [1], 43: [100]}, source='soidal-family+observed'),
         # Range, Precise, Penetrating, Explosive, Subobjects/Shots, Armor Pierce
    108: dict(name='Soidal Repeater', slot=256, tier=0, itemclass=3, usableby=[1], family='soidal',
         base=[], mods={13: 125, 14: 100, 32: 0, 34: 0, 36: 1, 43: 100}, seen={13: [125], 14: [100], 36: [1], 43: [100]}, source='guide+server'),
         # Range, Precise, Penetrating, Explosive, Subobjects/Shots, Armor Pierce
    
    109: dict(name='Bolt Thrower', slot=256, tier=4, itemclass=3, usableby=[1], family='bolt-thrower',
         base=[], mods={13: 80, 33: 1, 43: 100, 48: 0, 55: 20}, seen={13: [80], 33: [1], 43: [100], 48: [0], 55: [25]}, source='guide+observed'),
         # Range, Bounce, Armor Pierce, Trisected, Quick Shot / Anim Speed

    9: dict(name='Skein', slot=256, tier=0, itemclass=2, usableby=[2], family=None,
         base=[], mods={}, seen={}, source='none'),
         # no mods
    35: dict(name='Nacre Skein', slot=256, tier=1, itemclass=2, usableby=[2], family='skein',
         base=[], mods={24: 500, 25: 200, 50: 1, 51: 1, 53: 200}, seen={25: [200], 50: [1]}, source='guide+observed'),
         # Item Crit Chance, Item Crit Damage, Leech, Extra Hit, Move Time (ms)
    157: dict(name='Cobalt Skein', slot=256, tier=2, itemclass=2, usableby=[2], family='skein',
         base=[], mods={24: 500, 25: 200, 50: 1, 51: 1, 53: 200}, seen={}, source='guide'),
         # Item Crit Chance, Item Crit Damage, Leech, Extra Hit, Move Time (ms)
    158: dict(name='Sapphire Skein', slot=256, tier=3, itemclass=2, usableby=[2], family='skein',
         base=[], mods={24: 500, 25: 200, 50: 1, 51: 1, 53: 200}, seen={}, source='guide'),
         # Item Crit Chance, Item Crit Damage, Leech, Extra Hit, Move Time (ms)
    159: dict(name='Berylblade Skein', slot=256, tier=4, itemclass=2, usableby=[2], family='skein',
         base=[], mods={24: 500, 25: 200, 50: 1, 51: 1, 53: 200}, seen={50: [1], 51: [1], 53: [200]}, source='guide+observed'),
         # Item Crit Chance, Item Crit Damage, Leech, Extra Hit, Move Time (ms)
    215: dict(name='Vitreous Skein', slot=256, tier=5, itemclass=2, usableby=[2], family='skein',
         base=[], mods={24: 500, 25: 200, 50: 1, 51: 1, 53: 200}, seen={24: [500], 25: [200], 50: [1], 51: [1], 53: [200]}, source='guide+observed'),
         # Item Crit Chance, Item Crit Damage, Leech, Extra Hit, Move Time (ms)

    217: dict(name='Skyfire Skein', slot=256, tier=1, itemclass=2, usableby=[2], family='balefire-skein',
         base=[], mods={24: 500, 25: 200, 51: 1, 53: 200}, seen={24: [500], 25: [200], 51: [1], 53: [200]}, source='balefire-skein-family+server'),
         # Item Crit Chance, Item Crit Damage, Extra Hit, Move Time (ms)
    116: dict(name='Balefire Skein', slot=256, tier=3, itemclass=2, usableby=[2], family='balefire-skein',
         base=[], mods={24: 500, 25: 200, 51: 1, 53: 200}, seen={}, source='guide'),
         # Item Crit Chance, Item Crit Damage, Extra Hit, Move Time (ms)

    46: dict(name='Polychrome Skein', slot=256, tier=2, itemclass=2, usableby=[2], family='polychrome',
         base=[], mods={24: 500, 25: 200, 50: 1, 53: 200}, seen={24: [500], 25: [200], 50: [1], 53: [200]}, source='observed+server'),
         # Item Crit Chance, Item Crit Damage, Leech, Move Time (ms)
    216: dict(name='Motley', slot=256, tier=5, itemclass=2, usableby=[2], family='polychrome',
         base=[], mods={24: 500, 25: 200, 50: 1, 53: 200}, seen={25: [200]}, source='guide+observed'),
         # Item Crit Chance, Item Crit Damage, Leech, Move Time (ms)

    117: dict(name='Baetyl', slot=256, tier=4, itemclass=3, usableby=[2], family='baetyl',
         base=[], mods={13: 40, 24: 500, 25: 200, 45: 1}, seen={13: [40], 45: [1]}, doubles=[45], source='guide+observed'),
         # Range, Item Crit Chance, Item Crit Damage, Simultaneous

    6: dict(name='Sledge', slot=256, tier=0, itemclass=6, usableby=[3], family=None,
         base=[], mods={}, seen={}, source='none'),
         # no mods
    36: dict(name='Cruel Sledge', slot=256, tier=1, itemclass=6, usableby=[3], family='sledge',
         base=[], mods={22: 50, 24: 500, 25: 200, 37: 20, 43: 100, 51: 1}, seen={51: [1]}, source='guide+observed'),
         # Knockback Resist, Item Crit Chance, Item Crit Damage, Speed %, Armor Pierce, Extra Hit
    166: dict(name='Vengeful Sledge', slot=256, tier=2, itemclass=6, usableby=[3], family='sledge',
         base=[], mods={22: 50, 24: 500, 25: 200, 37: 20, 43: 100, 51: 1}, seen={25: [200]}, source='guide+observed'),
         # Knockback Resist, Item Crit Chance, Item Crit Damage, Speed %, Armor Pierce, Extra Hit
    167: dict(name='Sinful Sledge', slot=256, tier=3, itemclass=6, usableby=[3], family='sledge',
         base=[], mods={22: 50, 24: 500, 25: 200, 37: 20, 43: 100, 51: 1}, seen={}, source='guide'),
         # Knockback Resist, Item Crit Chance, Item Crit Damage, Speed %, Armor Pierce, Extra Hit
    168: dict(name='Baleful Sledge', slot=256, tier=4, itemclass=6, usableby=[3], family='sledge',
         base=[], mods={22: 50, 24: 500, 25: 200, 37: 20, 43: 100, 51: 1}, seen={22: [50], 25: [200]}, source='guide+observed'),
         # Knockback Resist, Item Crit Chance, Item Crit Damage, Speed %, Armor Pierce, Extra Hit
    223: dict(name='Corrupt Sledge', slot=256, tier=5, itemclass=6, usableby=[3], family='sledge',
         base=[], mods={22: 50, 24: 500, 25: 200, 37: 20, 43: 100, 51: 1}, seen={22: [50], 24: [500], 25: [200], 43: [100]}, source='guide+observed'),
         # Knockback Resist, Item Crit Chance, Item Crit Damage, Speed %, Armor Pierce, Extra Hit

    197: dict(name='Lancet', slot=256, tier=1, itemclass=6, usableby=[3], family='lancet',
         base=[], mods={22: 50, 37: 20, 43: 100, 45: 1}, seen={37: [20], 45: [1]}, doubles=[45], source='lancet-family+server'),
         # Knockback Resist, Speed %, Armor Pierce, Simultaneous; can roll twice: Simultaneous
    119: dict(name='Baculus', slot=256, tier=3, itemclass=6, usableby=[3], family='lancet',
         base=[], mods={22: 50, 37: 20, 43: 100, 45: 1}, seen={}, source='guide'),
         # Knockback Resist, Speed %, Armor Pierce, Simultaneous; can roll twice: Simultaneous

    47: dict(name='Adjudicator', slot=256, tier=2, itemclass=6, usableby=[3], family='adjudicator',
         base=[], mods={22: 50, 32: 0, 36: 2, 37: 20, 43: 100, 51: 1}, seen={22: [50], 36: [2], 37: [20], 51: [1]}, source='adjudicator-family+server'),
         # Knockback Resist, Penetrating, Subobjects/Shots, Speed %, Armor Pierce, Extra Hit
    224: dict(name='Quaestor', slot=256, tier=5, itemclass=6, usableby=[3], family='adjudicator',
         base=[], mods={22: 50, 32: 0, 36: 2, 37: 20, 43: 100, 51: 1}, seen={22: [50], 36: [2], 37: [20], 43: [100]}, source='guide+observed'),
         # Knockback Resist, Penetrating, Subobjects/Shots, Speed %, Armor Pierce, Extra Hit

    118: dict(name='Preceptor', slot=256, tier=4, itemclass=6, usableby=[3], family='preceptor',
         base=[], mods={22: 50, 36: 1, 37: 20, 38: 300, 43: 100}, seen={22: [50], 36: [1], 38: [300]}, doubles=[36], source='guide+observed'),
         # Knockback Resist, Subobjects/Shots (height), Speed %, Lifetime (ms), Armor Pierce; can roll twice: Shots

    53: dict(name='Dancer', slot=256, tier=0, itemclass=13, usableby=[5], family=None,
         base=[], mods={}, seen={}, source='none'),
         # no mods
    58: dict(name='Deepfire Dancer', slot=256, tier=1, itemclass=13, usableby=[5], family='dancer',
         base=[], mods={13: 100, 24: 500, 25: 200, 39: 0, 57: -50}, seen={13: [100], 24: [500], 25: [200], 39: [0], 57: [-50]}, doubles=[57], source='guide+observed+server'),
         # Range, Item Crit Chance, Item Crit Damage, Seeking, Cooldown; can roll twice: Cooldown
    175: dict(name='Everdawn Dancer', slot=256, tier=2, itemclass=13, usableby=[5], family='dancer',
         base=[], mods={13: 100, 24: 500, 25: 200, 39: 0, 57: -50}, seen={25: [200], 39: [0], 57: [-50]}, doubles=[57], source='guide+observed+server'),
         # Range, Item Crit Chance, Item Crit Damage, Seeking, Cooldown; can roll twice: Cooldown
    176: dict(name='Fellwhip Dancer', slot=256, tier=3, itemclass=13, usableby=[5], family='dancer',
         base=[], mods={13: 100, 24: 500, 25: 200, 39: 0, 57: -50}, seen={13: [100], 24: [500], 57: [-50]}, doubles=[57], source='guide+observed+server'),
         # Range, Item Crit Chance, Item Crit Damage, Seeking, Cooldown; can roll twice: Cooldown
    177: dict(name='Darkstar Dancer', slot=256, tier=4, itemclass=13, usableby=[5], family='dancer',
         base=[], mods={13: 100, 24: 500, 25: 200, 39: 0, 57: -50}, seen={13: [100], 24: [500], 25: [200], 39: [0], 57: [-50]}, doubles=[57], source='guide+observed'),
         # Range, Item Crit Chance, Item Crit Damage, Seeking, Cooldown; can roll twice: Cooldown
    229: dict(name='Direfall Dancer', slot=256, tier=5, itemclass=13, usableby=[5], family='dancer',
         base=[], mods={13: 100, 24: 500, 25: 200, 39: 0, 57: -50}, seen={13: [100], 24: [500], 25: [200], 39: [0], 57: [-50]}, doubles=[57], source='guide+observed+server'),
         # Range, Item Crit Chance, Item Crit Damage, Seeking, Cooldown; can roll twice: Cooldown

    199: dict(name='Telson', slot=256, tier=1, itemclass=13, usableby=[5], family='telson',
         base=[], mods={13: 100, 36: 2, 39: 0, 57: -50}, seen={}, doubles=[36, 57], source='guide+user'),
         # Range, Subobjects/Shots, Seeking, Cooldown; can roll twice: Subobjects/Shots, Cooldown
    113: dict(name='Gavotte', slot=256, tier=3, itemclass=13, usableby=[5], family='telson',
         base=[], mods={13: 100, 36: 2, 39: 0, 57: -50}, seen={57: [-50]}, doubles=[57], source='guide+server'),
         # Range, Subobjects/Shots, Seeking, Cooldown; can roll twice: Cooldown

    66: dict(name='Trinity', slot=256, tier=2, itemclass=13, usableby=[5], family='trinity',
         base=[], mods={13: 100, 24: 500, 36: 2, 57: -50}, seen={13: [100], 36: [1], 57: [-50]}, doubles=[36, 57], source='guide+server+user'),
         # Range, Item Crit Chance, Subobjects/Shots, Cooldown; can roll twice: Subobjects/Shots, Cooldown
    230: dict(name='Volta', slot=256, tier=5, itemclass=13, usableby=[5], family='trinity',
         base=[], mods={13: 100, 24: 500, 36: 2, 57: -50}, seen={24: [500], 36: [1], 57: [-50]}, doubles=[36, 57], source='guide+observed+user'),
         # Range, Item Crit Chance, Subobjects/Shots, Cooldown; can roll twice: Subobjects/Shots, Cooldown

    114: dict(name='Quickstep', slot=256, tier=4, itemclass=13, usableby=[5], family='quickstep',
         base=[], mods={13: 100, 24: 500, 25: 200, 57: -50}, seen={13: [100], 24: [500], 25: [200], 57: [-50]}, doubles=[57], source='guide+observed'),
         # Range, Item Crit Chance, Item Crit Damage, Cooldown; can roll twice: Cooldown

    193: dict(name='Needlebow', slot=256, tier=2, itemclass=3, usableby=[1, 2], family='bow',
         base=[], mods={13: 100, 32: 0, 33: 1, 43: 100}, seen={13: [100], 33: [1], 43: [100]}, doubles=[33], source='bow-family+server'),
         # Range, Penetrating, Bounce, Armor Pierce; can roll twice: Bounce
    144: dict(name='Stonebow', slot=256, tier=4, itemclass=3, usableby=[1, 2], family='bow',
         base=[], mods={13: 100, 32: 0, 33: 1, 43: 100}, seen={}, source='guide'),
         # Range, Penetrating, Bounce, Armor Pierce
    
    #
    #   SECONDARY
    #

    2: dict(name='Frag', slot=512, tier=0, itemclass=5, usableby=[1], family=None,
         base=[], mods={}, seen={}, source='none'),
         # no mods
    38: dict(name='Improved Frag', slot=512, tier=1, itemclass=5, usableby=[1], family='frag',
         base=[], mods={4: 1, 35: 0, 43: 100, 47: 0, 48: 0}, seen={4: [1]}, source='guide+observed'),
         # Max Ammo, Incendiary, Armor Pierce, Barbed, Trisected
    151: dict(name='Contrived Frag', slot=512, tier=2, itemclass=5, usableby=[1], family='frag',
         base=[], mods={4: 1, 35: 0, 43: 100, 47: 0, 48: 0}, seen={35: [0], 43: [100], 48: [0]}, source='guide+observed'),
         # Max Ammo, Incendiary, Armor Pierce, Barbed, Trisected
    152: dict(name='Synthetic Frag', slot=512, tier=3, itemclass=5, usableby=[1], family='frag',
         base=[], mods={4: 1, 35: 0, 43: 100, 47: 0, 48: 0}, seen={4: [1], 35: [0], 43: [100], 48: [0]}, source='guide+observed'),
         # Max Ammo, Incendiary, Armor Pierce, Barbed, Trisected
    153: dict(name='Reforged Frag', slot=512, tier=4, itemclass=5, usableby=[1], family='frag',
         base=[], mods={4: 1, 35: 0, 43: 100, 47: 0, 48: 0}, seen={4: [1], 35: [0], 47: [0], 48: [0]}, source='guide+observed'),
         # Max Ammo, Incendiary, Armor Pierce, Barbed, Trisected
    210: dict(name='Unstable Frag', slot=512, tier=5, itemclass=5, usableby=[1], family='frag',
         base=[], mods={4: 1, 35: 0, 43: 100, 47: 0, 48: 0}, seen={}, source='guide'),
         # Max Ammo, Incendiary, Armor Pierce, Barbed, Trisected

    39: dict(name='Cluster', slot=512, tier=2, itemclass=5, usableby=[1], family='cluster',
         base=[], mods={4: 2, 35: 0, 36: 1, 43: 100, 47: 0, 48: 0}, seen={}, source='guide'),
         # Max Ammo, Incendiary, Subobjects/Shots, Armor Pierce, Barbed, Trisected
    40: dict(name='Swarm Cluster', slot=512, tier=3, itemclass=5, usableby=[1], family='cluster',
         base=[], mods={4: 2, 36: 2, 43: 100, 47: 0, 48: 0}, seen={4: [2], 36: [2], 47: [0], 48: [0]}, doubles=[36], source='guide+observed+server'),
         # Max Ammo, Subobjects/Shots, Armor Pierce, Barbed, Trisected; can roll twice: Subobjects/Shots
    212: dict(name='Hydra', slot=512, tier=5, itemclass=5, usableby=[1], family='cluster',
         base=[], mods={4: 2, 36: 2, 43: 100, 47: 0, 48: 0}, seen={}, source='guide'),
         # Max Ammo, Subobjects/Shots, Armor Pierce, Barbed, Trisected

    194: dict(name='Tripwire', slot=512, tier=2, itemclass=5, usableby=[1], family='tripwire',
         base=[], mods={4: 2, 35: 0, 43: 100, 47: 0, 48: 0}, seen={4: [2], 35: [0], 48: [0]}, source='tripwire-family+server'),
         # Max Ammo, Incendiary, Armor Pierce, Barbed, Trisected
    110: dict(name='Proxies', slot=512, tier=4, itemclass=5, usableby=[1], family='tripwire',
         base=[], mods={4: 2, 35: 0, 43: 100, 47: 0, 48: 0}, seen={4: [2], 43: [100], 47: [0], 48: [0]}, source='guide+observed'),
         # Max Ammo, Incendiary, Armor Pierce, Barbed, Trisected

    1: dict(name='Aesc', slot=512, tier=0, itemclass=4, usableby=[2], family='aesc',
         base=[], mods={}, seen={}, source='user'),
         # no mods
    41: dict(name='Biting Aesc', slot=512, tier=1, itemclass=4, usableby=[2], family='aesc',
         base=[], mods={4: 2, 13: 100, 24: 500, 37: 80, 45: 1}, seen={45: [1]}, doubles=[45], source='guide+server'),
         # Max Ammo, Range, Item Crit Chance, Speed %, Simultaneous; can roll twice: Simultaneous
    160: dict(name='Falcate Aesc', slot=512, tier=2, itemclass=4, usableby=[2], family='aesc',
         base=[], mods={4: 2, 13: 100, 24: 500, 37: 80, 45: 1}, seen={45: [1]}, doubles=[45], source='guide+server'),
         # Max Ammo, Range, Item Crit Chance, Speed %, Simultaneous; can roll twice: Simultaneous
    161: dict(name='Keen Aesc', slot=512, tier=3, itemclass=4, usableby=[2], family='aesc',
         base=[], mods={4: 2, 13: 100, 24: 500, 37: 80, 45: 1}, seen={4: [2], 13: [100], 37: [80], 45: [1]}, doubles=[45], source='guide+observed+server'),
         # Max Ammo, Range, Item Crit Chance, Speed %, Simultaneous; can roll twice: Simultaneous
    162: dict(name='Violet Aesc', slot=512, tier=4, itemclass=4, usableby=[2], family='aesc',
         base=[], mods={4: 2, 13: 100, 24: 500, 37: 80, 45: 1}, seen={13: [100], 37: [80], 45: [1]}, doubles=[45], source='guide+observed+server'),
         # Max Ammo, Range, Item Crit Chance, Speed %, Simultaneous; can roll twice: Simultaneous
    218: dict(name='Radiant Aesc', slot=512, tier=5, itemclass=4, usableby=[2], family='aesc',
         base=[], mods={4: 2, 13: 100, 24: 500, 37: 80, 45: 1}, seen={45: [1]}, doubles=[45], source='guide+server'),
         # Max Ammo, Range, Item Crit Chance, Speed %, Simultaneous; can roll twice: Simultaneous

    195: dict(name='Haunting Aesc', slot=512, tier=1, itemclass=4, usableby=[2], family='haunting-aesc',
         base=[], mods={4: 2, 13: 100, 24: 500, 37: 80, 45: 1}, seen={13: [100], 37: [80]}, source='haunting-aesc-family+server'),
         # Max Ammo, Range, Item Crit Chance, Speed %, Simultaneous
    72: dict(name='Gnawing Aesc', slot=512, tier=3, itemclass=4, usableby=[2], family='haunting-aesc',
         base=[], mods={4: 2, 13: 100, 24: 500, 37: 80, 45: 1}, seen={}, source='guide'),
         # Max Ammo, Range, Item Crit Chance, Speed %, Simultaneous

    111: dict(name='Kulbeda', slot=512, tier=2, itemclass=4, usableby=[2], family='kulbeda',
         base=[], mods={4: 2, 24: 500, 33: 1, 37: 80, 38: 1000, 45: 1}, seen={33: [1], 37: [80], 45: [1]}, source='kulbeda-family+server'),
         # Max Ammo, Item Crit Chance, Bounce, Speed %, Lifetime (ms), Simultaneous
    219: dict(name='Kunai', slot=512, tier=5, itemclass=4, usableby=[2], family='kulbeda',
         base=[], mods={4: 2, 24: 500, 33: 1, 37: 80, 38: 1000, 45: 1}, seen={24: [500], 33: [1], 45: [1]}, doubles=[45], source='guide+observed+server'),
         # Max Ammo, Item Crit Chance, Bounce, Speed %, Lifetime (ms), Simultaneous; can roll twice: Simultaneous

    7: dict(name='Kyeser', slot=512, tier=0, itemclass=7, usableby=[3], family=None,
         base=[], mods={}, seen={}, source='none'),
         # no mods
    44: dict(name='Irascent Kyeser', slot=512, tier=1, itemclass=7, usableby=[3], family='kyeser',
         base=[], mods={4: 2, 39: 0, 42: 40, 43: 100, 48: 0}, seen={42: [40]}, source='guide+observed'),
         # Max Ammo, Seeking, Acceleration, Armor Pierce, Trisected
    169: dict(name='Caustic Kyeser', slot=512, tier=2, itemclass=7, usableby=[3], family='kyeser',
         base=[], mods={4: 2, 39: 0, 42: 40, 43: 100, 48: 0}, seen={39: [0]}, source='guide+observed'),
         # Max Ammo, Seeking, Acceleration, Armor Pierce, Trisected
    170: dict(name='Insidious Kyeser', slot=512, tier=3, itemclass=7, usableby=[3], family='kyeser',
         base=[], mods={4: 2, 39: 0, 42: 40, 43: 100, 48: 0}, seen={}, source='guide'),
         # Max Ammo, Seeking, Acceleration, Armor Pierce, Trisected
    171: dict(name='Nefarious Kyeser', slot=512, tier=4, itemclass=7, usableby=[3], family='kyeser',
         base=[], mods={4: 2, 39: 0, 42: 40, 43: 100, 48: 0}, seen={}, source='guide'),
         # Max Ammo, Seeking, Acceleration, Armor Pierce, Trisected
    226: dict(name='Diabolical Kyeser', slot=512, tier=5, itemclass=7, usableby=[3], family='kyeser',
         base=[], mods={4: 2, 39: 0, 42: 40, 43: 100, 48: 0}, seen={4: [2], 39: [0], 43: [100], 48: [0]}, source='guide+observed'),
         # Max Ammo, Seeking, Acceleration, Armor Pierce, Trisected

    312: dict(name='Triad', slot=512, tier=1, itemclass=7, usableby=[3], family='swarmer',
         base=[], mods={4: 2, 36: 1, 39: 0, 42: 40, 43: 100, 48: 0}, seen={39: [0], 43: [100]}, source='swarmer-family+server'),
         # Max Ammo, Subobjects/Shots, Seeking, Acceleration, Armor Pierce, Trisected
    45: dict(name='Swarmer', slot=512, tier=3, itemclass=7, usableby=[3], family='swarmer',
         base=[], mods={4: 2, 36: 1, 39: 0, 42: 40, 43: 100, 48: 0}, seen={}, source='guide'),
         # Max Ammo, Subobjects/Shots, Seeking, Acceleration, Armor Pierce, Trisected
    227: dict(name='Locust', slot=512, tier=5, itemclass=7, usableby=[3], family='swarmer',
         base=[], mods={4: 2, 36: 2, 39: 0, 42: 40, 43: 100, 48: 0}, seen={4: [2], 36: [2], 43: [100]}, source='guide+observed'),
         # Max Ammo, Subobjects/Shots, Seeking, Acceleration, Armor Pierce, Trisected

    198: dict(name='Hotfoot', slot=512, tier=2, itemclass=7, usableby=[3], family='hotfoot',
         base=[], mods={4: 2, 36: 2, 39: 0, 42: 40, 43: 100, 46: 2, 48: 0}, seen={4: [2], 39: [0], 42: [40], 43: [100], 46: [2]}, doubles=[46], source='hotfoot-family+server'),
         # Max Ammo, Subobjects/Shots, Seeking, Acceleration, Armor Pierce, Secondary Subobjects, Trisected; can roll twice: Secondary Subobjects
    115: dict(name='Burner', slot=512, tier=4, itemclass=7, usableby=[3], family='hotfoot',
         base=[], mods={4: 2, 36: 2, 39: 0, 42: 40, 43: 100, 46: 2, 48: 0}, seen={42: [40], 43: [100], 46: [2]}, doubles=[46], source='guide+server'),
         # Max Ammo, Subobjects/Shots, Seeking, Acceleration, Armor Pierce, Secondary Subobjects, Trisected; can roll twice: Secondary Subobjects

    54: dict(name='Antiphon', slot=512, tier=0, itemclass=14, usableby=[5], family='antiphon',
         base=[], mods={}, seen={}, source='user'),
         # no mods
    59: dict(name='Defiant Antiphon', slot=512, tier=1, itemclass=14, usableby=[5], family='antiphon',
         base=[], mods={32: 0, 36: 1, 38: 2000, 46: 5, 54: 50, 55: 40}, seen={32: [0], 36: [1]}, doubles=[36], source='guide+observed+server'),
         # Penetrating, Subobjects/Shots, Lifetime (ms), Secondary Subobjects, Item Armor, Quick Shot / Anim Speed; can roll twice: Subobjects/Shots
    178: dict(name='Invidious Antiphon', slot=512, tier=2, itemclass=14, usableby=[5], family='antiphon',
         base=[], mods={32: 0, 36: 1, 38: 2000, 46: 5, 54: 50, 55: 40}, seen={32: [0], 36: [1], 54: [50], 55: [40]}, doubles=[36], source='guide+observed+server'),
         # Penetrating, Subobjects/Shots, Lifetime (ms), Secondary Subobjects, Item Armor, Quick Shot / Anim Speed; can roll twice: Subobjects/Shots
    179: dict(name='Mocking Antiphon', slot=512, tier=3, itemclass=14, usableby=[5], family='antiphon',
         base=[], mods={32: 0, 36: 1, 38: 2000, 46: 5, 54: 50, 55: 40}, seen={32: [0], 36: [1], 38: [2000], 54: [50], 55: [40]}, doubles=[36], source='guide+observed+server'),
         # Penetrating, Subobjects/Shots, Lifetime (ms), Secondary Subobjects, Item Armor, Quick Shot / Anim Speed; can roll twice: Subobjects/Shots
    180: dict(name='Profane Antiphon', slot=512, tier=4, itemclass=14, usableby=[5], family='antiphon',
         base=[], mods={32: 0, 36: 1, 38: 2000, 46: 5, 54: 50, 55: 40}, seen={36: [1], 38: [2000], 54: [50], 55: [40]}, doubles=[36], source='guide+server'),
         # Penetrating, Subobjects/Shots, Lifetime (ms), Secondary Subobjects, Item Armor, Quick Shot / Anim Speed; can roll twice: Subobjects/Shots
    232: dict(name='Blasphemous Antiphon', slot=512, tier=5, itemclass=14, usableby=[5], family='antiphon',
         base=[], mods={32: 0, 36: 1, 38: 2000, 46: 5, 54: 50, 55: 40}, seen={32: [0], 36: [1], 38: [2000], 54: [50], 55: [40]}, doubles=[36], source='guide+observed+server'),
         # Penetrating, Subobjects/Shots, Lifetime (ms), Secondary Subobjects, Item Armor, Quick Shot / Anim Speed; can roll twice: Subobjects/Shots

    311: dict(name='Silent Antiphon', slot=512, tier=1, itemclass=14, usableby=[5], family='antiphon',
         base=[], mods={32: 0, 36: 1, 38: 2000, 46: 5, 54: 50, 55: 40}, seen={32: [0], 36: [1], 38: [2000], 54: [50], 55: [40]}, source='antiphon-family+server'),
         # Penetrating, Subobjects/Shots, Lifetime (ms), Secondary Subobjects, Item Armor, Quick Shot / Anim Speed (pool of the Antiphon family)
    67: dict(name='Whispered Antiphon', slot=512, tier=4, itemclass=14, usableby=[5], family='whispered-antiphon',
         base=[], mods={32: 0, 36: 1, 38: 2000, 46: 5, 54: 50, 55: 40}, seen={32: [0], 36: [1], 38: [2000], 54: [50]}, source='guide+observed+server'),
         # Penetrating, Subobjects/Shots, Lifetime (ms), Secondary Subobjects, Item Armor, Quick Shot / Anim Speed

    200: dict(name='Mangonel', slot=512, tier=2, itemclass=14, usableby=[5], family='mangonel',
         base=[], mods={32: 0, 54: 50, 55: 40, 57: -200}, seen={32: [0], 54: [50], 55: [30], 57: [-250]}, source='mangonel-family+server'),
         # Penetrating, Item Armor, Quick Shot / Anim Speed, Cooldown
    233: dict(name='Scorpion', slot=512, tier=5, itemclass=14, usableby=[5], family='mangonel',
         base=[], mods={32: 0, 54: 50, 55: 40, 57: -200}, seen={54: [50]}, source='guide+observed'),
         # Penetrating, Item Armor, Quick Shot / Anim Speed, Cooldown

    #
    #   SPECIAL
    #

    63: dict(name='Blast', slot=768, tier=0, itemclass=16, usableby=[1], family=None,
         base=[], mods={}, seen={}, source='none'),
         # no mods
    69: dict(name='Empowered Blast', slot=768, tier=1, itemclass=16, usableby=[1], family='blast',
         base=[], mods={21: 1, 36: 1, 43: 100, 48: 0}, seen={21: [1], 36: [1]}, doubles=[36], source='guide+observed'),
         # Air Dashes, Subobjects/Shots, Armor Pierce, Trisected; can roll twice: Subobjects/Shots
    154: dict(name='Withering Blast', slot=768, tier=2, itemclass=16, usableby=[1], family='blast',
         base=[], mods={21: 1, 36: 1, 43: 100, 48: 0}, seen={21: [1], 36: [1]}, doubles=[36], source='guide+server'),
         # Air Dashes, Subobjects/Shots, Armor Pierce, Trisected; can roll twice: Subobjects/Shots
    155: dict(name='Voracious Blast', slot=768, tier=3, itemclass=16, usableby=[1], family='blast',
         base=[], mods={21: 1, 36: 1, 43: 100, 48: 0}, seen={21: [1], 36: [1]}, doubles=[36], source='guide+observed+server'),
         # Air Dashes, Subobjects/Shots, Armor Pierce, Trisected; can roll twice: Subobjects/Shots
    156: dict(name='Zealous Blast', slot=768, tier=4, itemclass=16, usableby=[1], family=None,
         base=[], mods={21: 1, 36: 1, 43: 100, 48: 0}, seen={21: [1], 36: [1], 43: [100], 48: [0]}, doubles=[36], source='server'),
         # Air Dashes, Subobjects/Shots, Armor Pierce, Trisected; can roll twice: Subobjects/Shots
    213: dict(name='Furious Blast', slot=768, tier=5, itemclass=16, usableby=[1], family='blast',
         base=[], mods={21: 1, 36: 1, 43: 100, 48: 0}, seen={21: [1], 36: [1]}, doubles=[36], source='guide+observed'),
         # Air Dashes, Subobjects/Shots, Armor Pierce, Trisected; can roll twice: Subobjects/Shots

    70: dict(name='Forceful Blast', slot=768, tier=3, itemclass=16, usableby=[1], family='forceful-blast',
         base=[], mods={21: 1, 36: 1, 43: 100, 48: 0}, seen={36: [1]}, doubles=[36], source='guide+server'),
         # Air Dashes, Subobjects/Shots, Armor Pierce, Trisected; can roll twice: Subobjects/Shots
    214: dict(name='Fireform', slot=768, tier=5, itemclass=16, usableby=[1], family='forceful-blast',
         base=[], mods={21: 1, 36: 1, 43: 100, 48: 0}, seen={36: [1]}, doubles=[36], source='guide+server'),
         # Air Dashes, Subobjects/Shots, Armor Pierce, Trisected; can roll twice: Subobjects/Shots

    71: dict(name='Scattered Blast', slot=768, tier=4, itemclass=16, usableby=[1], family='scattered-blast',
         base=[], mods={21: 1, 36: 2, 43: 100, 48: 0}, seen={21: [1], 36: [2], 43: [100]}, doubles=[36], source='guide+observed+server'),
         # Air Dashes, Subobjects/Shots, Armor Pierce, Trisected; can roll twice: Subobjects/Shots

    10: dict(name='Warp', slot=768, tier=0, itemclass=10, usableby=[2], family=None,
         base=[], mods={}, seen={}, source='none'),
         # no mods
    42: dict(name='Acrotic Warp', slot=768, tier=1, itemclass=10, usableby=[2], family='warp',
         base=[], mods={21: 1, 24: 500, 25: 200, 37: 80, 38: 150}, seen={}, source='guide'),
         # Air Dashes, Item Crit Chance, Item Crit Damage, Speed %, Lifetime (ms)
    163: dict(name='Beloid Warp', slot=768, tier=2, itemclass=10, usableby=[2], family='warp',
         base=[], mods={21: 1, 24: 500, 25: 200, 37: 80, 38: 150}, seen={24: [500], 25: [200], 38: [150]}, source='guide+observed'),
         # Air Dashes, Item Crit Chance, Item Crit Damage, Speed %, Lifetime (ms)
    164: dict(name='Daedal Warp', slot=768, tier=3, itemclass=10, usableby=[2], family='warp',
         base=[], mods={21: 1, 24: 500, 25: 200, 37: 80, 38: 150}, seen={25: [200], 38: [150]}, source='guide+observed'),
         # Air Dashes, Item Crit Chance, Item Crit Damage, Speed %, Lifetime (ms)
    165: dict(name='Aeon Warp', slot=768, tier=4, itemclass=10, usableby=[2], family='warp',
         base=[], mods={21: 1, 24: 500, 25: 200, 37: 80, 38: 150}, seen={}, source='guide'),
         # Air Dashes, Item Crit Chance, Item Crit Damage, Speed %, Lifetime (ms)
    221: dict(name='Tacent Warp', slot=768, tier=5, itemclass=10, usableby=[2], family='warp',
         base=[], mods={21: 1, 24: 500, 25: 200, 37: 80, 38: 150}, seen={21: [1], 24: [500], 25: [200], 37: [80], 38: [150]}, source='guide+observed'),
         # Air Dashes, Item Crit Chance, Item Crit Damage, Speed %, Lifetime (ms)

    196: dict(name='Residual Warp', slot=768, tier=2, itemclass=10, usableby=[2], family='residual-warp',
         base=[], mods={21: 1, 24: 500, 25: 200, 37: 80, 38: 150}, seen={}, source='residual-warp-family+server'),
         # Air Dashes, Item Crit Chance, Item Crit Damage, Speed %, Lifetime (ms)
    98: dict(name='Abiding Warp', slot=768, tier=4, itemclass=10, usableby=[2], family='residual-warp',
         base=[], mods={21: 1, 24: 500, 25: 200, 37: 80, 38: 150}, seen={}, source='guide'),
         # Air Dashes, Item Crit Chance, Item Crit Damage, Speed %, Lifetime (ms)

    112: dict(name='Mirrored Warp', slot=768, tier=3, itemclass=10, usableby=[2], family=None,
         base=[], mods={21: 1, 24: 500, 25: 200, 37: 80, 38: 150}, seen={21: [1], 24: [500], 25: [200], 37: [80], 38: [150]}, source='observed+server'),
         # Air Dashes, Item Crit Chance, Item Crit Damage, Speed %, Lifetime (ms)
    222: dict(name='Mimic', slot=768, tier=5, itemclass=10, usableby=[2], family='mirrored-warp',
         base=[], mods={21: 1, 24: 500, 25: 200, 37: 80, 38: 150}, seen={21: [1], 24: [500], 37: [80], 38: [150]}, source='guide+observed'),
         # Air Dashes, Item Crit Chance, Item Crit Damage, Speed %, Lifetime (ms)

    11: dict(name='Mantlet', slot=768, tier=0, itemclass=19, usableby=[3], family=None,
         base=[(10, 2)], mods={}, seen={}, source='none'),
         # no mods
    32: dict(name='Relentless Mantlet', slot=768, tier=1, itemclass=19, usableby=[3], family='mantlet',
         base=[(10, 4)], mods={22: 50, 37: 40, 42: 40, 52: 0}, seen={37: [40], 42: [40]}, source='guide+observed'),
         # Knockback Resist, Speed %, Acceleration, Reflect
    172: dict(name='Fortified Mantlet', slot=768, tier=2, itemclass=19, usableby=[3], family='mantlet',
         base=[(10, 8)], mods={22: 50, 37: 40, 42: 40, 52: 0}, seen={}, source='guide'),
         # Knockback Resist, Speed %, Acceleration, Reflect
    173: dict(name='Banded Mantlet', slot=768, tier=3, itemclass=19, usableby=[3], family='mantlet',
         base=[(10, 12)], mods={22: 50, 37: 40, 42: 40, 52: 0}, seen={52: [0]}, source='guide+observed'),
         # Knockback Resist, Speed %, Acceleration, Reflect
    174: dict(name='Annealed Mantlet', slot=768, tier=4, itemclass=19, usableby=[3], family='mantlet',
         base=[(10, 16)], mods={22: 50, 37: 40, 42: 40, 52: 0}, seen={}, source='guide'),
         # Knockback Resist, Speed %, Acceleration, Reflect
    228: dict(name='Eternal Mantlet', slot=768, tier=5, itemclass=19, usableby=[3], family='mantlet',
         base=[(10, 20)], mods={22: 50, 37: 40, 42: 40, 52: 0}, seen={22: [50], 37: [40], 42: [40], 52: [0]}, source='guide+observed'),
         # Knockback Resist, Speed %, Acceleration, Reflect

    12: dict(name='Macron', slot=768, tier=0, itemclass=12, usableby=[5], family=None,
         base=[], mods={}, seen={}, source='none'),
         # no mods
    48: dict(name='Protracted Macron', slot=768, tier=1, itemclass=12, usableby=[5], family='macron',
         base=[], mods={35: 0, 38: 1000, 43: 100, 45: 1, 46: 5, 56: 0}, seen={46: [5], 56: [0]}, source='guide+observed'),
         # Incendiary, Lifetime (ms), Armor Pierce, Simultaneous, Secondary Subobjects, Shielded
    181: dict(name='Recalcitant Macron', slot=768, tier=2, itemclass=12, usableby=[5], family='macron',
         base=[], mods={35: 0, 38: 1000, 43: 100, 45: 1, 46: 5, 56: 0}, seen={}, source='guide'),
         # Incendiary, Lifetime (ms), Armor Pierce, Simultaneous, Secondary Subobjects, Shielded
    182: dict(name='Inveterate Macron', slot=768, tier=3, itemclass=12, usableby=[5], family='macron',
         base=[], mods={35: 0, 38: 1000, 43: 100, 45: 1, 46: 5, 56: 0}, seen={}, source='guide'),
         # Incendiary, Lifetime (ms), Armor Pierce, Simultaneous, Secondary Subobjects, Shielded
    183: dict(name='Composite Macron', slot=768, tier=4, itemclass=12, usableby=[5], family='macron',
         base=[], mods={35: 0, 38: 1000, 43: 100, 45: 1, 46: 5, 56: 0}, seen={38: [1000], 43: [100], 46: [5], 56: [0]}, source='guide+observed'),
         # Incendiary, Lifetime (ms), Armor Pierce, Simultaneous, Secondary Subobjects, Shielded
    234: dict(name='Devoted Macron', slot=768, tier=5, itemclass=12, usableby=[5], family='macron',
         base=[], mods={35: 0, 38: 1000, 43: 100, 45: 1, 46: 5, 56: 0}, seen={}, source='guide'),
         # Incendiary, Lifetime (ms), Armor Pierce, Simultaneous, Secondary Subobjects, Shielded

    68: dict(name='Mechanized Macron', slot=768, tier=2, itemclass=12, usableby=[5], family='mechanized-macron',
         base=[], mods={35: 0, 38: 1000, 43: 100, 45: 1, 46: 5, 56: 0}, seen={}, source='mechanized-macron-family+server'),
         # Incendiary, Lifetime (ms), Armor Pierce, Simultaneous, Secondary Subobjects, Shielded
    235: dict(name='Skiff', slot=768, tier=4, itemclass=12, usableby=[5], family='mechanized-macron',
         base=[], mods={35: 0, 38: 1000, 43: 100, 45: 1, 46: 5, 56: 0}, seen={45: [1], 46: [5], 56: [0]}, source='guide+observed'),
         # Incendiary, Lifetime (ms), Armor Pierce, Simultaneous, Secondary Subobjects, Shielded

    305: dict(name='Blink', slot=768, tier=5, itemclass=12, usableby=[5], family='blink',
         base=[], mods={35: 0, 38: 1000, 43: 100, 45: 1, 46: 5, 56: 0}, seen={35: [0], 38: [1000], 43: [100], 45: [1], 46: [5]}, source='guide+observed'),
         # Incendiary, Lifetime (ms), Armor Pierce, Simultaneous, Secondary Subobjects, Shielded

    #
    #   MOBILITY
    #

    261: dict(name='Talons', slot=1280, tier=1, itemclass=None, usableby=[1], family='talons',
         base=[(10, 3)], mods={11: 2, 12: 5, 20: 25, 23: 100}, seen={11: [2], 12: [5], 23: [100]}, source='guide+observed'),
         # Movement Speed, Jump Height, Crit Damage, Crit Chance
    262: dict(name='Durable Talons', slot=1280, tier=2, itemclass=None, usableby=[1], family='talons',
         base=[(10, 6)], mods={11: 2, 12: 5, 20: 25, 23: 100}, seen={}, source='guide'),
         # Movement Speed, Jump Height, Crit Damage, Crit Chance
    263: dict(name='Augmented Talons', slot=1280, tier=3, itemclass=None, usableby=[1], family='talons',
         base=[(10, 9)], mods={11: 2, 12: 5, 20: 25, 23: 100}, seen={11: [2]}, source='guide+observed'),
         # Movement Speed, Jump Height, Crit Damage, Crit Chance
    264: dict(name='Reinforced Talons', slot=1280, tier=4, itemclass=None, usableby=[1], family='talons',
         base=[(10, 12)], mods={11: 2, 12: 5, 20: 25, 23: 100}, seen={11: [2], 12: [5], 20: [25], 23: [100]}, source='guide+observed'),
         # Movement Speed, Jump Height, Crit Damage, Crit Chance
    265: dict(name='Resilient Talons', slot=1280, tier=5, itemclass=None, usableby=[1], family='talons',
         base=[(10, 15)], mods={11: 2, 12: 5, 20: 25, 23: 100}, seen={}, source='guide'),
         # Movement Speed, Jump Height, Crit Damage, Crit Chance

    15: dict(name='Trackers', slot=1280, tier=1, itemclass=None, usableby=[1, 2], family='trackers',
         base=[(11, 3), (23, 50)], mods={12: 5, 18: 3, 20: 50}, seen={18: [3], 20: [50]}, source='guide+observed'),
         # Jump Height, Damage %, Crit Damage
    258: dict(name='Durable Trackers', slot=1280, tier=2, itemclass=None, usableby=[1, 2], family='trackers',
         base=[(11, 6), (23, 100)], mods={12: 5, 18: 3, 20: 50}, seen={18: [3], 20: [50]}, source='guide+observed'),
         # Jump Height, Damage %, Crit Damage
    184: dict(name='Augmented Trackers', slot=1280, tier=3, itemclass=None, usableby=[2], family='trackers',
         base=[(11, 9), (23, 150)], mods={12: 5, 18: 3, 20: 50}, seen={18: [3], 20: [50]}, source='guide+observed'),
         # Jump Height, Damage %, Crit Damage
    259: dict(name='Reinforced Trackers', slot=1280, tier=4, itemclass=None, usableby=[2], family='trackers',
         base=[(11, 12), (23, 200)], mods={12: 5, 18: 3, 20: 50}, seen={18: [3], 20: [50]}, source='guide+observed'),
         # Jump Height, Damage %, Crit Damage
    260: dict(name='Resilient Trackers', slot=1280, tier=5, itemclass=None, usableby=[2], family='trackers',
         base=[(11, 15), (23, 250)], mods={12: 5, 18: 3, 20: 50}, seen={12: [5], 18: [3], 20: [50]}, source='guide+observed'),
         # Jump Height, Damage %, Crit Damage

    43: dict(name='Sabatons', slot=1280, tier=1, itemclass=None, usableby=[3], family='sabatons',
         base=[(10, 4)], mods={11: 3, 12: 1, 18: 5}, seen={11: [3], 18: [5]}, source='guide+observed'),
         # Movement Speed, Jump Height, Damage %
    267: dict(name='Durable Sabatons', slot=1280, tier=2, itemclass=None, usableby=[3], family='sabatons',
         base=[(10, 8)], mods={11: 3, 12: 1, 18: 5}, seen={}, source='guide'),
         # Movement Speed, Jump Height, Damage %
    185: dict(name='Augmented Sabatons', slot=1280, tier=3, itemclass=None, usableby=[3], family='sabatons',
         base=[(10, 12)], mods={11: 3, 12: 1, 18: 5}, seen={11: [3], 12: [1], 18: [5]}, source='guide+observed'),
         # Movement Speed, Jump Height, Damage %
    268: dict(name='Reinforced Sabatons', slot=1280, tier=4, itemclass=None, usableby=[3], family='sabatons',
         base=[(10, 16)], mods={11: 3, 12: 1, 18: 5}, seen={11: [3], 12: [1], 18: [5]}, source='guide+observed'),
         # Movement Speed, Jump Height, Damage %
    269: dict(name='Resilient Sabatons', slot=1280, tier=5, itemclass=None, usableby=[3], family='sabatons',
         base=[(10, 20)], mods={11: 3, 12: 1, 18: 5}, seen={11: [3], 12: [1], 18: [5]}, source='guide+observed'),
         # Movement Speed, Jump Height, Damage %

    187: dict(name='Stompers', slot=1280, tier=3, itemclass=None, usableby=[3], family='stompers',
         base=[(18, 20)], mods={10: 2, 18: 10}, seen={10: [2], 18: [10]}, source='stompers-family+server+user'),
         # Armor, Damage %
    270: dict(name='Spiked Stompers', slot=1280, tier=5, itemclass=None, usableby=[3], family='stompers',
         base=[(18, 30), (10, 4), (23, 100), (20, 25)], mods={10: 4, 18: 20}, seen={}, source='guide'),
         # Armor, Damage %

    61: dict(name='Valenki', slot=1280, tier=1, itemclass=None, usableby=[5], family='valenki',
         base=[(10, 2), (11, 4)], mods={11: 4, 20: 50, 23: 200}, seen={11: [4], 20: [50]}, source='guide+observed'),
         # Movement Speed, Crit Damage, Crit Chance
    271: dict(name='Durable Valenki', slot=1280, tier=2, itemclass=None, usableby=[5], family='valenki',
         base=[(10, 4), (11, 7)], mods={11: 4, 20: 50, 23: 200}, seen={}, source='guide'),
         # Movement Speed, Crit Damage, Crit Chance
    186: dict(name='Augmented Valenki', slot=1280, tier=3, itemclass=None, usableby=[5], family='valenki',
         base=[(10, 6), (11, 10)], mods={11: 4, 20: 50, 23: 200}, seen={11: [4], 20: [50]}, source='guide+observed'),
         # Movement Speed, Crit Damage, Crit Chance
    272: dict(name='Reinforced Valenki', slot=1280, tier=4, itemclass=None, usableby=[5], family='valenki',
         base=[(10, 8), (11, 13)], mods={11: 4, 20: 50, 23: 200}, seen={11: [4], 20: [50]}, source='guide+observed'),
         # Movement Speed, Crit Damage, Crit Chance
    273: dict(name='Resilient Valenki', slot=1280, tier=5, itemclass=None, usableby=[5], family='valenki',
         base=[(10, 10), (11, 16)], mods={11: 4, 20: 50, 23: 200}, seen={11: [4], 23: [200]}, source='guide+observed'),
         # Movement Speed, Crit Damage, Crit Chance

    146: dict(name='Lightfoot', slot=1280, tier=4, itemclass=None, usableby=[5], family='lightfoot',
         base=[(49, -30)], mods={10: 2, 49: -10}, seen={}, source='guide'),
         # Armor, Gravity %

    16: dict(name='Empyreals', slot=1280, tier=2, itemclass=None, usableby=[1, 2], family=None,
         base=[(8, 1)], mods={10: 2, 11: 5, 12: 5}, seen={10: [2], 11: [5], 12: [5]}, source='observed'),
         # Armor, Movement Speed, Jump Height
    266: dict(name='Aeonic Empyreals', slot=1280, tier=5, itemclass=None, usableby=[1, 2], family='empyreals',
         base=[(8, 2)], mods={10: 4, 11: 10, 12: 10, 20: 50, 23: 300}, seen={10: [4], 20: [50]}, source='guide+observed'),
         # Armor, Movement Speed, Jump Height, Crit Damage, Crit Chance

    105: dict(name='Gliders', slot=1280, tier=2, itemclass=21, usableby=[3, 5], family='gliders',
         base=[], mods={10: 2, 11: 5, 12: 5}, seen={10: [2], 12: [5]}, source='gliders-family+server'),
         # Armor, Movement Speed, Jump Height
    106: dict(name='Volatile Gliders', slot=1280, tier=4, itemclass=21, usableby=[3, 5], family='gliders',
         base=[], mods={10: 3, 11: 5, 12: 5}, seen={}, source='guide'),
         # Armor, Movement Speed, Jump Height

    277: dict(name='Boosters', slot=1280, tier=5, itemclass=21, usableby=[3, 5], family=None,
         base=[], mods={10: 5, 11: 5, 12: 5}, seen={10: [5], 11: [5], 12: [5]}, source='server'),
         # Armor, Movement Speed, Jump Height
    274: dict(name='Overloaded Boosters', slot=1280, tier=5, itemclass=21, usableby=[3, 5], family='boosters',
         base=[], mods={10: 5, 11: 5, 12: 5}, seen={}, source='guide'),
         # Armor, Movement Speed, Jump Height

    #
    #   BODY
    #

    14: dict(name='Jerkin', slot=1024, tier=1, itemclass=None, usableby=[1], family='jerkin',
         base=[(10, 5), (11, -2)], mods={11: 4, 18: 5, 23: 100}, seen={18: [5], 23: [100]}, source='guide+observed'),
         # Movement Speed, Damage %, Crit Chance
    55: dict(name='Durable Jerkin', slot=1024, tier=2, itemclass=None, usableby=[1], family='jerkin',
         base=[(10, 10), (11, -2)], mods={11: 4, 18: 5, 23: 100}, seen={11: [4], 18: [5], 23: [100]}, source='guide+observed'),
         # Movement Speed, Damage %, Crit Chance
    247: dict(name='Augmented Jerkin', slot=1024, tier=3, itemclass=None, usableby=[1], family='jerkin',
         base=[(10, 15), (11, -2)], mods={11: 4, 18: 5, 23: 100}, seen={11: [4], 18: [5], 23: [100]}, source='guide+observed'),
         # Movement Speed, Damage %, Crit Chance
    248: dict(name='Reinforced Jerkin', slot=1024, tier=4, itemclass=None, usableby=[1], family='jerkin',
         base=[(10, 20), (11, -2)], mods={11: 4, 18: 5, 23: 100}, seen={11: [4], 18: [5], 23: [100]}, source='guide+observed'),
         # Movement Speed, Damage %, Crit Chance
    249: dict(name='Resilient Jerkin', slot=1024, tier=5, itemclass=None, usableby=[1], family='jerkin',
         base=[(10, 25), (11, -2)], mods={11: 4, 18: 5, 23: 100}, seen={11: [4], 18: [5], 23: [100]}, source='guide+observed'),
         # Movement Speed, Damage %, Crit Chance

    34: dict(name='Hyrst', slot=1024, tier=1, itemclass=None, usableby=[1, 2], family='hyrst',
         base=[(10, 2), (11, 3)], mods={11: 5, 20: 25, 23: 200}, seen={11: [5], 20: [25], 23: [200]}, doubles=[23], source='guide+observed+server'),
         # Movement Speed, Crit Damage, Crit Chance; can roll twice: Crit Chance
    103: dict(name='Durable Hyrst', slot=1024, tier=2, itemclass=None, usableby=[2, 1], family='hyrst',
         base=[(10, 4), (11, 4)], mods={11: 5, 20: 25, 23: 200}, seen={20: [25], 23: [200]}, doubles=[23], source='guide+observed+server'),
         # Movement Speed, Crit Damage, Crit Chance; can roll twice: Crit Chance
    250: dict(name='Augmented Hyrst', slot=1024, tier=3, itemclass=None, usableby=[2], family='hyrst',
         base=[(10, 6), (11, 5)], mods={11: 5, 20: 25, 23: 200}, seen={23: [200]}, doubles=[23], source='guide+server'),
         # Movement Speed, Crit Damage, Crit Chance; can roll twice: Crit Chance
    251: dict(name='Reinforced Hyrst', slot=1024, tier=4, itemclass=None, usableby=[2], family='hyrst',
         base=[(10, 8), (11, 6)], mods={11: 5, 20: 25, 23: 200}, seen={23: [200]}, doubles=[23], source='guide+server'),
         # Movement Speed, Crit Damage, Crit Chance; can roll twice: Crit Chance
    252: dict(name='Resilient Hyrst', slot=1024, tier=5, itemclass=None, usableby=[2], family='hyrst',
         base=[(10, 10), (11, 7)], mods={11: 5, 20: 25, 23: 200}, seen={11: [5], 20: [25], 23: [200]}, doubles=[23], source='guide+observed'),
         # Movement Speed, Crit Damage, Crit Chance; can roll twice: Crit Chance

    33: dict(name='Plating', slot=1024, tier=1, itemclass=None, usableby=[3], family='plating',
         base=[(10, 8), (11, -4)], mods={11: 5, 18: 5}, seen={18: [5]}, doubles=[18], source='guide+server'),
         # Movement Speed, Damage %; can roll twice: Damage %
    102: dict(name='Durable Plating', slot=1024, tier=2, itemclass=None, usableby=[3], family='plating',
         base=[(10, 16), (11, -4)], mods={11: 5, 18: 5}, seen={18: [5]}, doubles=[18], source='guide+server'),
         # Movement Speed, Damage %; can roll twice: Damage %
    244: dict(name='Augmented Plating', slot=1024, tier=3, itemclass=None, usableby=[3], family='plating',
         base=[(10, 24), (11, -4)], mods={11: 5, 18: 5}, seen={11: [5], 18: [5]}, doubles=[18], source='guide+observed+server'),
         # Movement Speed, Damage %; can roll twice: Damage %
    245: dict(name='Reinforced Plating', slot=1024, tier=4, itemclass=None, usableby=[3], family=None,
         base=[(10, 32), (11, -4)], mods={11: 5, 18: 5}, seen={11: [5], 18: [5]}, doubles=[18], source='observed'),
         # Movement Speed, Damage %; can roll twice: Damage %
    246: dict(name='Resilient Plating', slot=1024, tier=5, itemclass=None, usableby=[3], family='plating',
         base=[(10, 40), (11, -4)], mods={11: 5, 18: 5}, seen={11: [5], 18: [5]}, doubles=[18], source='guide+observed'),
         # Movement Speed, Damage %; can roll twice: Damage %

    60: dict(name='Woven', slot=1024, tier=1, itemclass=None, usableby=[5], family='woven',
         base=[(10, 3), (11, 3)], mods={11: 5, 20: 25, 23: 200}, seen={11: [5], 20: [25], 23: [200]}, doubles=[11], source='guide+observed+server'),
         # Movement Speed, Crit Damage, Crit Chance; can roll twice: Movement Speed
    104: dict(name='Durable Woven', slot=1024, tier=2, itemclass=None, usableby=[5], family='woven',
         base=[(10, 6), (11, 4)], mods={11: 5, 20: 25, 23: 200}, seen={23: [200]}, doubles=[11], source='guide+server'),
         # Movement Speed, Crit Damage, Crit Chance; can roll twice: Movement Speed
    253: dict(name='Augmented Woven', slot=1024, tier=3, itemclass=None, usableby=[5], family='woven',
         base=[(10, 9), (11, 5)], mods={11: 5, 20: 25, 23: 200}, seen={11: [5], 20: [25], 23: [200]}, doubles=[11], source='guide+observed+server'),
         # Movement Speed, Crit Damage, Crit Chance; can roll twice: Movement Speed
    254: dict(name='Reinforced Woven', slot=1024, tier=4, itemclass=None, usableby=[5], family='woven',
         base=[(10, 12), (11, 6)], mods={11: 5, 20: 25, 23: 200}, seen={11: [5], 20: [25], 23: [200]}, doubles=[11], source='guide+observed'),
         # Movement Speed, Crit Damage, Crit Chance; can roll twice: Movement Speed
    255: dict(name='Resilient Woven', slot=1024, tier=5, itemclass=None, usableby=[5], family='woven',
         base=[(10, 15), (11, 7)], mods={11: 5, 20: 25, 23: 200}, seen={11: [5], 20: [25]}, doubles=[11], source='guide+observed'),
         # Movement Speed, Crit Damage, Crit Chance; can roll twice: Movement Speed

    191: dict(name='Blockers', slot=1024, tier=2, itemclass=20, usableby=[5], family='blockers',
         base=[], mods={36: 1}, seen={36: [1]}, source='blockers-family+server'),
         # Subobjects/Shots
    192: dict(name='Enraged Blockers', slot=1024, tier=4, itemclass=20, usableby=[5], family='blockers',
         base=[], mods={36: 1}, seen={36: [1]}, source='server'),
         # Subobjects/Shots
    257: dict(name='Enlarged Blockers', slot=1024, tier=5, itemclass=20, usableby=[5], family='blockers',
         base=[], mods={36: 1}, seen={36: [1]}, source='server'),
         # Subobjects/Shots

    188: dict(name='Bandolier', slot=1024, tier=2, itemclass=None, usableby=[1, 2, 3], family='bandolier',
         base=[], mods={4: 1}, seen={4: [1]}, source='bandolier-family+server'),
         # Max Ammo
    189: dict(name='Double Bandolier', slot=1024, tier=4, itemclass=None, usableby=[1, 2, 3], family='bandolier',
         base=[(27, 2)], mods={4: 1}, seen={}, source='guide'),
         # Max Ammo
    190: dict(name='Berserker', slot=1024, tier=3, itemclass=None, usableby=[1, 2, 3], family='berserker',
         base=[(18, 40), (10, -20)], mods={10: 5, 18: 20}, seen={10: [5], 18: [20]}, source='guide+user'),
         # Armor, Damage %
    256: dict(name='Frenzied Berserker', slot=1024, tier=5, itemclass=None, usableby=[1, 2, 3], family='berserker',
         base=[(18, 60), (10, -30), (23, 300), (20, 100)], mods={10: 20, 18: 40}, seen={10: [20], 18: [40]}, source='guide+observed'),
         # Armor, Damage %

    #
    #   IMPLANT
    #

    76: dict(name='Inferior Salites', slot=1536, tier=3, itemclass=None, usableby=[], family=None,
         base=[(2, 20)], mods={}, seen={}, source='observed'),
    77: dict(name='Salites', slot=1536, tier=5, itemclass=None, usableby=[], family=None,
         base=[(2, 40)], mods={}, seen={}, source='none'),
    82: dict(name='Inferior Calites', slot=1536, tier=3, itemclass=None, usableby=[], family=None,
         base=[], mods={}, seen={}, source='server'),
    83: dict(name='Calites', slot=1536, tier=5, itemclass=None, usableby=[], family=None,
         base=[], mods={}, seen={}, source='server'),
    73: dict(name='Inferior Bellites', slot=1536, tier=3, itemclass=None, usableby=[], family=None,
         base=[(18, 20)], mods={}, seen={}, source='none'),
    74: dict(name='Bellites', slot=1536, tier=5, itemclass=None, usableby=[], family=None,
         base=[(18, 40)], mods={}, seen={}, source='observed'),
    85: dict(name='Inferior Armites', slot=1536, tier=3, itemclass=None, usableby=[], family=None,
         base=[(10, 10)], mods={}, seen={}, source='observed'),
    86: dict(name='Armites', slot=1536, tier=5, itemclass=None, usableby=[], family=None,
         base=[], mods={}, seen={}, source='server'),
    299: dict(name='Inferior Velites', slot=1536, tier=3, itemclass=None, usableby=[], family=None,
         base=[(11, 10)], mods={}, seen={}, source='none'),
    300: dict(name='Velites', slot=1536, tier=5, itemclass=None, usableby=[], family=None,
         base=[(11, 20)], mods={}, seen={}, source='server'),
    89: dict(name='Inferior Emites', slot=1536, tier=3, itemclass=None, usableby=[], family=None,
         base=[(12, 10)], mods={}, seen={}, source='observed'),
    79: dict(name='Inferior Delites', slot=1536, tier=3, itemclass=None, usableby=[], family=None,
         base=[(23, 600)], mods={}, seen={}, source='server'),
    80: dict(name='Delites', slot=1536, tier=5, itemclass=None, usableby=[], family=None,
         base=[(23, 1200)], mods={}, seen={}, source='none'),
    308: dict(name='Inferior Ultrites', slot=1536, tier=3, itemclass=None, usableby=[], family=None,
         base=[(18, 10), (2, 10), (23, 300), (20, 50), (4, 1), (10, 5), (12, 5), (11, 5)], mods={}, seen={}, source='none'),
    309: dict(name='Ultrites', slot=1536, tier=5, itemclass=None, usableby=[], family=None,
         base=[(18, 20), (2, 20), (23, 600), (20, 100), (4, 2), (10, 10), (12, 10), (11, 10)], mods={}, seen={}, source='none'),
    302: dict(name='Inferior Firites', slot=1536, tier=3, itemclass=None, usableby=[], family=None,
         base=[(22, 25)], mods={}, seen={}, source='none'),
    303: dict(name='Firites', slot=1536, tier=5, itemclass=None, usableby=[], family=None,
         base=[(22, 50)], mods={}, seen={}, source='none'),
    88: dict(name='Exites', slot=1536, tier=5, itemclass=None, usableby=[], family=None,
         base=[(8, 1)], mods={}, seen={}, source='none'),
}

# Pickup items (slot None: health / boost pickups, keys and the like): kept out of
# ITEMS and the Lootr window, but still known (new_items.py treats them as seen).
UNUSED_ITEMS = {
    #
    #   PICKUP
    #

    18: dict(name='Health Boost 1', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(1, 25)], mods={1: 25}, seen={1: [25]}, source='observed'),
    21: dict(name='Ammo Boost', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(3, 1)], mods={3: 1}, seen={3: [1]}, source='observed'),

    49: dict(name='1 EC', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(16, 1)], mods={16: 1}, seen={16: [1]}, source='observed'),
    96: dict(name='5 EC', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(16, 5)], mods={16: 5}, seen={16: [5]}, source='observed'),
    50: dict(name='10 EC', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(16, 10)], mods={16: 10}, seen={16: [10]}, source='observed'),
    97: dict(name='25 EC', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(16, 25)], mods={16: 25}, seen={16: [25]}, source='observed'),

    291: dict(name='1 UC', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(26, 1)], mods={}, seen={}, source='none'),
    292: dict(name='5 UC', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(26, 5)], mods={}, seen={}, source='none'),

    99: dict(name='Fungus Cave Key', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(44, 1)], mods={}, seen={}, source='server'),
    201: dict(name='Vanquished Key', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(44, 1)], mods={}, seen={}, source='server'),
    100: dict(name='Underground Base Key', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[], mods={}, seen={}, source='server'),
    107: dict(name='Strands Key', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[], mods={}, seen={}, source='server'),
    101: dict(name='Graveyard Key', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[], mods={}, seen={}, source='server'),
    145: dict(name='Temple of the Lost Key', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(44, 1)], mods={}, seen={}, source='none'),
    205: dict(name='Unknown Key', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(44, 1)], mods={}, seen={}, source='none'),
    206: dict(name='Mysterious Key', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(44, 1)], mods={}, seen={}, source='none'),

    #
    #   BOOST
    #

    19: dict(name='Max Health Boost 1', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(2, 2)], mods={2: 2}, seen={2: [2]}, source='observed'),
    20: dict(name='Max Health Boost 2', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(2, 2)], mods={2: 2}, seen={2: [2]}, source='observed'),
    92: dict(name='Max Health Boost 3', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(2, 2)], mods={2: 2}, seen={2: [2]}, source='observed'),
    93: dict(name='Max Health Boost 4', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(2, 2)], mods={}, seen={}, source='none'),
    236: dict(name='Max Health Boost 5', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(2, 2)], mods={}, seen={}, source='none'),

    22: dict(name='Max Ammo Boost 1', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(4, 1)], mods={}, seen={}, source='none'),
    23: dict(name='Max Ammo Boost 2', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(4, 1)], mods={4: 1}, seen={4: [1]}, source='observed'),
    94: dict(name='Max Ammo Boost 3', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(4, 1)], mods={4: 1}, seen={4: [1]}, source='observed'),
    95: dict(name='Max Ammo Boost 4', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(4, 1)], mods={4: 1}, seen={4: [1]}, source='observed'),
    237: dict(name='Max Ammo Boost 5', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(4, 1)], mods={}, seen={}, source='none'),

    132: dict(name='Damage Boost 1', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(18, 2)], mods={18: 2}, seen={18: [2]}, source='observed'),
    133: dict(name='Damage Boost 2', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(18, 2)], mods={18: 2}, seen={18: [2]}, source='observed'),
    134: dict(name='Damage Boost 3', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(18, 2)], mods={18: 2}, seen={18: [2]}, source='observed'),
    135: dict(name='Damage Boost 4', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(18, 2)], mods={18: 2}, seen={18: [2]}, source='observed'),
    241: dict(name='Damage Boost 5', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(18, 2)], mods={}, seen={}, source='none'),

    120: dict(name='Armor Boost 1', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(10, 1)], mods={10: 1}, seen={10: [1]}, source='observed'),
    121: dict(name='Armor Boost 2', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(10, 1)], mods={10: 1}, seen={10: [1]}, source='observed'),
    122: dict(name='Armor Boost 3', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(10, 1)], mods={}, seen={}, source='none'),
    123: dict(name='Armor Boost 4', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(10, 1)], mods={10: 1}, seen={10: [1]}, source='observed'),
    238: dict(name='Armor Boost 5', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(10, 1)], mods={}, seen={}, source='none'),

    124: dict(name='Movement Speed Boost 1', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(11, 1)], mods={11: 1}, seen={11: [1]}, source='observed'),
    125: dict(name='Movement Speed Boost 2', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[], mods={}, seen={}, source='server'),
    126: dict(name='Movement Speed Boost 3', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(11, 1)], mods={11: 1}, seen={11: [1]}, source='observed'),
    127: dict(name='Movement Speed Boost 4', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(11, 1)], mods={}, seen={}, source='none'),
    239: dict(name='Movement Speed Boost 5', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(11, 1)], mods={}, seen={}, source='none'),

    128: dict(name='Jump Height Boost 1', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(12, 1)], mods={12: 1}, seen={12: [1]}, source='observed'),
    129: dict(name='Jump Height Boost 2', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(12, 1)], mods={12: 1}, seen={12: [1]}, source='observed'),
    130: dict(name='Jump Height Boost 3', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(12, 1)], mods={12: 1}, seen={12: [1]}, source='observed'),
    131: dict(name='Jump Height Boost 4', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(12, 1)], mods={12: 1}, seen={12: [1]}, source='observed'),
    240: dict(name='Jump Height Boost 5', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(12, 1)], mods={}, seen={}, source='none'),

    136: dict(name='Crit Chance Boost 1', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(23, 25)], mods={23: 25}, seen={23: [25]}, source='observed'),
    137: dict(name='Crit Chance Boost 2', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(23, 25)], mods={23: 25}, seen={23: [25]}, source='observed'),
    138: dict(name='Crit Chance Boost 3', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(23, 25)], mods={23: 25}, seen={23: [25]}, source='observed'),
    139: dict(name='Crit Chance Boost 4', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(23, 25)], mods={}, seen={}, source='none'),
    242: dict(name='Crit Chance Boost 5', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(23, 25)], mods={}, seen={}, source='none'),

    140: dict(name='Crit Damage Boost 1', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(20, 20)], mods={20: 20}, seen={20: [20]}, source='observed'),
    141: dict(name='Crit Damage Boost 2', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(20, 20)], mods={20: 20}, seen={20: [20]}, source='observed'),
    142: dict(name='Crit Damage Boost 3', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(20, 20)], mods={20: 20}, seen={20: [20]}, source='observed'),
    143: dict(name='Crit Damage Boost 4', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(20, 20)], mods={}, seen={}, source='none'),
    243: dict(name='Crit Damage Boost 5', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(20, 20)], mods={}, seen={}, source='none'),

    51: dict(name='Implant Slot 1', slot=None, tier=None, itemclass=None, usableby=[], family=None,
         base=[(17, 1)], mods={17: 1}, seen={17: [1]}, source='observed'),

    #
    #   COSMETIC (unorganized)
    #

    278: dict(name='Repurposed Helmet', slot=None, tier=None, itemclass=None, usableby=[1], family=None,
         base=[(60, None)], mods={}, seen={}, source='none'),
    279: dict(name='Silver Headguard', slot=None, tier=None, itemclass=None, usableby=[1, 2, 5], family=None,
         base=[(60, None)], mods={}, seen={}, source='none'),
    280: dict(name='Red Beret', slot=None, tier=None, itemclass=None, usableby=[1, 2, 5], family=None,
         base=[(60, None)], mods={}, seen={}, source='none'),
    281: dict(name='Bunny Mask', slot=None, tier=None, itemclass=None, usableby=[1, 2, 5], family=None,
         base=[(60, None)], mods={}, seen={}, source='none'),
    282: dict(name='Worn Stockman', slot=None, tier=None, itemclass=None, usableby=[1, 2, 5], family=None,
         base=[(60, 0)], mods={}, seen={}, source='none'),
    283: dict(name='The Goggles', slot=None, tier=None, itemclass=None, usableby=[1, 2, 5], family=None,
         base=[(60, None)], mods={}, seen={}, source='none'),
    286: dict(name='Cloth Plate', slot=None, tier=None, itemclass=None, usableby=[3], family=None,
         base=[(60, None)], mods={}, seen={}, source='none'),
    287: dict(name='Fox Plate', slot=None, tier=None, itemclass=None, usableby=[3], family=None,
         base=[(60, None)], mods={}, seen={}, source='none'),
    288: dict(name='Scarred Plate', slot=None, tier=None, itemclass=None, usableby=[3], family=None,
         base=[(60, 0)], mods={}, seen={}, source='none'),
    290: dict(name='Blue Paisley Bandana', slot=None, tier=None, itemclass=None, usableby=[5], family=None,
         base=[(60, None)], mods={}, seen={}, source='none'),
    293: dict(name='Laughing Skull', slot=None, tier=None, itemclass=None, usableby=[1, 2], family=None,
         base=[(60, 0)], mods={}, seen={}, source='server'),
    294: dict(name='Grey Visor', slot=None, tier=None, itemclass=None, usableby=[1, 2, 5], family=None,
         base=[(60, 0)], mods={}, seen={}, source='none'),
    295: dict(name='Fox Ears', slot=None, tier=None, itemclass=None, usableby=[1, 2, 5], family=None,
         base=[(60, 0)], mods={}, seen={}, source='none'),
    297: dict(name='Newsboy', slot=None, tier=None, itemclass=None, usableby=[1, 2, 5], family=None,
         base=[], mods={}, seen={}, source='server'),
    298: dict(name='Blindfold', slot=None, tier=None, itemclass=None, usableby=[1, 2, 5], family=None,
         base=[], mods={}, seen={}, source='server'),

    306: dict(name='Berserker Skin', slot=None, tier=None, itemclass=None, usableby=[1], family=None,
         base=[], mods={}, seen={}, source='server'),
    307: dict(name='Killer Skin', slot=None, tier=None, itemclass=None, usableby=[2], family=None,
         base=[], mods={}, seen={}, source='server'),
}


def item_by_name(name):
    """Look up an item record by name (case-insensitive)."""
    name = name.lower()
    for type_, rec in list(ITEMS.items()) + list(UNUSED_ITEMS.items()):
        if rec['name'].lower() == name:
            return type_, rec
    return None, None


def possible_mods(type_):
    """[(stat id, stat name, default value)] for every mod that can roll on an item."""
    rec = ITEMS.get(type_) or UNUSED_ITEMS.get(type_)
    if not rec:
        return []
    return [(s, STAT_NAMES.get(s, '?'), v) for s, v in rec['mods'].items()]


def describe_mods(statboosts):
    """Readable text for an item instance's statboosts [(stat, val), ...]."""
    return ', '.join('{}={}'.format(STAT_NAMES.get(s, s), v) for s, v in statboosts)


# the pick-up matrix ##########################################################
# Columns: the item's rank, as the game names it (rankUtil::getRankName: the number of
# statboosts on the item, a mod rolled twice counting twice, at most 4): 0 Stock,
# 1 Modified, 2 Custom, 3 Experimental, 4 Prototype. Rows: the mods that can roll on the
# item, plus a "x2" row for a mod it can roll twice. Marks (rules[item][rank][row key]):
# 1 check (want), -1 X (don't want), missing = -- (wildcard).

RANKS = ['Stock', 'Modified', 'Custom', 'Experimental', 'Prototype']
NO_MODS = 'pickup'          # row key of the one Stock cell of an item no mods roll on


def rank_of(statboosts):
    '''the item's column: how many mods it has, as the game counts them for its name'''
    return min(len(statboosts), len(RANKS) - 1)


def max_mods(type_):
    '''the most mods an item can have: one per mod in its pool, two for a mod it can
    roll twice, 4 at most (the game's ranks)'''
    rec = ITEMS.get(type_) or UNUSED_ITEMS.get(type_) or {}
    return min(len(RANKS) - 1, len(rec.get('mods', ())) + len(rec.get('doubles', ())))


def matrix_rows(type_):
    '''[(row key, row name, columns)] for an item: a row per mod that can roll, then
    "<mod> x2" (key "<stat>x2", columns Custom and up) for a mod that can roll twice.
    Only the columns up to the most mods the item can have.'''
    rec = ITEMS.get(type_) or UNUSED_ITEMS.get(type_)
    if not rec:
        return []
    top = max_mods(type_) + 1
    rows = []
    for stat in rec['mods']:
        name = STAT_NAMES.get(stat, '?')
        rows.append((str(stat), name, list(range(top))))
        if stat in rec.get('doubles', ()):
            rows.append(('%dx2' % stat, name + ' x2', list(range(2, top))))
    if not rows:            # nothing rolls on it: it only comes Stock, so one Stock cell
        rows.append((NO_MODS, 'No mods: use the Stock header', [0]))
    return rows


ANY = 'any'                 # rules[item][mod count]['any']: 1 = ANY (whole column), -1 = NONE


def wants(rules, type_, statboosts):
    '''should Lootr pick this item up? statboosts: [stat id, ...] of the dropped item
    (a mod rolled twice is in it twice). The item's rank picks the column; then:
    any of its mods marked X there -> no; else it must have every mod checked there
    (a "<mod> x2" check needs that mod twice) -> yes; no check in the column -> no.
    A column's header switches it (rules[item][count]['any']): 1 = ANY, every item of
    that column except one with an X mod; -1 = NONE, no item of that column. Stock (no
    mods, no cells) has only its header: ANY takes stock ones, anything else leaves them.'''
    col = rules.get(str(type_), {}).get(str(rank_of(statboosts)), {})
    mode = col.get(ANY, 0)
    if mode == -1:
        return False
    if not statboosts:
        return mode == 1
    counts = {}
    for s in statboosts:
        counts[s] = counts.get(s, 0) + 1
    has = set()                 # the row keys this item matches
    for s, n in counts.items():
        has.add(str(s))
        if n >= 2:
            has.add('%dx2' % s)
    if any(col.get(key) == -1 for key in has):
        return False
    if mode == 1:
        return True
    wanted = [key for key, v in col.items() if v == 1 and key != ANY]
    return bool(wanted) and all(key in has for key in wanted)


# game functions (mvmmoclient.exe, base 0x400000): address, first bytes. If a game
# update moves them the bytes differ and the Lootr window stays off instead of crashing.
FUNCS = {
    'new':            (0x637a30, '5583ec588d442450c744'),   # operator new(unsigned)
    'delete':         (0x637970, '8b44240485c07408e9b7'),   # operator delete(void *)
    'string':         (0x5dde00, '565383ec1489ce8b5c24'),   # std::string(const char *, const allocator &)
    'optionsDialog':  (0x499b70, '5589e5565381ecd00000'),   # OptionsDialog(const char *title, w, h)
    'checkboxLine':   (0x4931b0, '5589e55383ec648d5df8'),   # CheckboxLine(const char *label)
    'dropdownLine':   (0x493c90, '5589e55383ec648d55f8'),   # DropdownLine(label, current, std::string *opts, n)
    'dropdown':       (0x45d8f0, '5589e557565381ec8c00'),   # Dropdown(w, h, current, std::string *opts, n)
    'label':          (0x461120, '5589e583ec788d55f889'),   # Label(text, font, size, color, outline, outlineColor, maxW)
    'addChild':       (0x467b40, '5589e583ec688d45f889'),   # UIElementContainer::addChild(UIElement *)
    'deleteChild':    (0x467980, '5589e55383ec148b5d08'),   # UIElementContainer::deleteChild(UIElement *)
    'setCurrent':     (0x45d880, '5589e58b493cc9e9343a'),   # Dropdown::setCurrent(const char *)
    'setText':        (0x4612c0, '5589e557565383ec1c8d'),   # Label::setText(const char *)
    'setColor':       (0x45fa80, '5589e557565383ec1c89'),   # Label::setColor(uint32_t argb)
    'closeManager':   (0x5fc5c0, '5589e55383ec148b4510'),   # std::function manager of bind(deleteChild, GameMenu*, dialog)
    'closeInvoker':   (0x6080e0, '5589e55383ec148b4508'),   # ... and its invoker (as GameMenu::controls uses)
    'dialogButton':   (0x45d530, '5589e583ec788d55f889'),   # DialogButton(text, id, w, h) (Done, Reset To Defaults)
    'dialog':         (0x45c4d0, '5589e557565381ecfc00'),   # Dialog(title, message, ok, cancel) ("Area not safe")
    'cancelManager':  (0x5fc520, '5589e55383ec148b4510'),   # std::function manager of bind(deleteChild, parent, dialog)
    'cancelInvoker':  (0x6080b0, '5589e55383ec148b4508'),   # ... and its invoker (as GameMenu::exitGame uses)
    'tmGet':          (0x47e9d0, '5589e583ec588d45f8c7'),   # TextureManager::get() (the one TextureManager)
    'tmFind':         (0x47ea90, '5589e5565389ce83ec20'),   # TextureManager::find(const char *vid) -> Visual *
    'drawObjVisual':  (0x4d0e30, '5589e5575683ec608d7d'),   # WorldView::drawObjectVisual(obj): how loot is drawn
    'getItem':        (0x41bd00, '5581c18402000089e550'),   # PlayerCharacter::getItem(slotpos) -> Item * (or NULL)
    'itemLibGet':     (0x43d160, '5589e583ec588d45f8c7'),   # ItemLibrary::get() (the one ItemLibrary)
    'itemLookup':     (0x43d370, '5589e5508d4508890424'),   # ItemLibrary::lookup(type) -> ItemDescription * (or NULL)
    'lootCtor':       (0x442450, '5589e583ec788d55f889'),   # Loot::Loot(subWorld, objId, Properties &, ItemProperties &, autoApply)
    'propsCtor':      (0x55d5d0, '55c7018869680089e55d'),   # Properties::Properties()
}
CONTAINER_VT = 0x68a988     # plain UIElementContainer vtable
DIALOG_W = 500              # OptionsDialog size used by Gameplay / Graphics / Controls (the smallest)
DIALOG_FILL = 0.85          # the Lootr window takes this much of the screen (it centres itself)
LINE_CHECKBOX = 0x30        # CheckboxLine / DropdownLine: their Checkbox / Dropdown
CHECKBOX_ON = 0x34          # Checkbox: checked byte (GameplayOptions::refresh writes it)
BUTTON_CLICK = 0x2c         # DialogButton: Handler<> run on click
RESET_BUTTON = 0x44         # OptionsDialog: its Reset To Defaults DialogButton (+0x40 is Done)
CONFIRM_OK, CONFIRM_CANCEL = 0x2c, 0x3c     # Dialog: Handler<>s of its OK / Cancel (and Esc)
BUTTON_W, BUTTON_H = 0xa4, 0x30     # Done / Reset To Defaults size
LINE_X, LINE_Y, LINE_GAP = 60, 60, 16   # settings rows: x = 60, first y = 60, then + h + 16
DROPDOWN_LABEL = 0x3c       # Dropdown: the Label showing the current choice
DIALOG_CLOSE = 0x2c         # Dialog: Handler<> fired by Done / Esc (counter, then vector begin/end/cap)
DROPDOWN_CHANGE = 0x2c      # Dropdown: Handler<std::string> its popup fires with the clicked option
NATIVE_VERSION = 19       # bump when Native changes (it is kept in refs across reloads)
HANDLER_ENTRY = 0x14        # one callback: id, std::function (storage 8, manager, invoker)
ITEM_PAGE = 20              # items per page in the Item dropdown (its list is one column)
WHITE, BLACK = 0xffffffff, 0xff000000
ORANGE, CYAN = 0xffff9b00, 0xff07d8bb       # Controls: column headers, key cells (ARGB)
GREEN, RED = 0xff3cdc3c, 0xffff4b4b

# Highlight Items / Magnify Items: drawn over loot on the ground that the table wants
HIGHLIGHT_LINE, HIGHLIGHT_FILL = 0xe03cdc3c, 0x403cdc3c     # ARGB box around it
HIGHLIGHT_W = 2             # outline width, px
MAGNIFY = 3                 # the enlarged sprite above it: this many times its size
MAGNIFY_GAP = 6             # px between the item and the enlarged sprite

# Show Chest Contents: a Chest holds its items (Chest.items, ItemProperties) from the start;
# Chest.pos is -1 until it is opened, then the index of the next item it throws (one every
# 200 ms, Chest::internalUpdate -> throwLoot). Items at index >= pos are still inside.
HP_STAT = 1                 # HP pickups heal (stat HP)
CHEST_MAX = 6               # most sprites shown above one chest
CHEST_GAP = 4               # px between them (normal size)
CHEST_LIFT = 10             # px more between the chest and them than MAGNIFY_GAP
CHEST_SUBWORLD = 0x134      # ClientObject.subWorld (Chest::throwLoot passes it to Loot::Loot)
CHEST_POS, CHEST_COUNT = 0x158, 0x140   # Chest.pos, Chest.items.current_size (elements at 0x13c)
OBJ_CENTRED = 0x8d          # WorldObject byte: drawn from its centre, not its bottom (drawImage)

# Auto Loot: press interact when the item you stand on is wanted. The key goes to the
# game's own keyboardCallback(down, SDL keycode, userData) as a real key press would
# (with SBPE's keyboard patch, through refs.sendKey instead).
KEYBOARD_CB = (0x464c70, '5589e583ec188b4d108b')    # keyboardCallback (unhooked bytes)
INTERACT_KEY = 'A'          # default interact key (SDL key name), as the game's default controls
PICK_HOLD = 0.06            # s the interact key is held (a 40 ms world step must see it)
PICK_RETRY = 0.5            # s before pressing again for the same item
PICK_CONFIRM = 2.0          # s to wait for a pressed item to disappear (= picked up)
BAG_SLOTS = range(0xF00, 0xF08)     # the 8 backpack slots (inv_api names them invSlot1-8)
FULL_EVERY = 5.0            # s between "Inventory Full" messages
MSG_TIME, MSG_RISE = 1.6, 40    # floating message: seconds shown, px it rises
MSG_SIZE = 16
MSG_GREEN, MSG_RED = 0x3cdc3c, 0xff4b4b

# items you drop from your inventory: never auto looted, a yellow box instead of the green one
MINE_LINE, MINE_FILL = 0xe0ffd700, 0x40ffd700
OWN_SLOTS = list(range(0x100, 0x700, 0x100)) + list(range(0xF00, 0xF08))   # equipped + backpack
DROP_MATCH = 3.0            # s between an item leaving your inventory and its loot appearing
DROP_NEAR = 200             # px: your drop lands this close to you

# window layout, as the Controls page: orange headers, white row names, cyan cells
MARGIN = 40                 # left / right edge of the window contents
TOP_Y = 60                  # below the title
DD_GAP = 12                 # between the three dropdowns
DD_W = (('class', 130), ('slot', 120), ('item', 250))
DD_H = 0x20                 # dropdown height (as DropdownLine)
TABLE_GAP = 40              # dropdowns -> table
NAME_W = 220                # mod name column
COL_MIN, COL_MAX = 115, 150     # mod-count columns (Controls: 150 apart)
ROW_H = 36                  # Controls rows are 36 px apart
COLUMNS = RANKS              # 0..4 mods, as the game names the item
CELL = {0: ('--', CYAN), 1: ('√', GREEN), -1: ('×', RED)}       # neutral, check, X
HEAD_LOOK = {0: ('', ORANGE), 1: ('ANY ', GREEN), -1: ('NONE ', RED)}   # column header: tag, color
CELL_FONT = b'HemiHeadBold'    # Controls' key font: has the check (U+221A) and X (U+00D7)


def _u32(v):
    return struct.pack('<I', int(v) & 0xffffffff)


class ExecMemory(object):
    '''a page of executable memory for the small call thunks below'''
    def __init__(self, size=4096):
        import cffi
        self.kffi = cffi.FFI()
        self.kffi.cdef('void * __stdcall VirtualAlloc(void *, size_t, unsigned long, unsigned long);')
        p = self.kffi.dlopen('kernel32.dll').VirtualAlloc(self.kffi.NULL, size, 0x3000, 0x40)
        if p == self.kffi.NULL:
            raise MemoryError('VirtualAlloc failed')
        self.base = int(self.kffi.cast('uintptr_t', p))
        self.page = p
        self.used = 0

    def put(self, code):
        addr = self.base + self.used
        self.kffi.memmove(self.kffi.cast('char *', addr), code, len(code))
        self.used += (len(code) + 15) & ~15
        return addr


def thunk_thiscall_to_cdecl(target, nargs):
    '''__thiscall entry point calling cdecl target(this, arg1..argN)'''
    code = b'\x55\x89\xe5'
    for i in reversed(range(nargs)):
        code += b'\xff\x75' + bytes([8 + 4 * i])
    code += b'\x51' + b'\xb8' + _u32(target) + b'\xff\xd0'
    code += b'\x89\xec\x5d' + b'\xc2' + struct.pack('<H', 4 * nargs)
    return code


def thunk_cdecl_to_thiscall(target, nargs):
    '''cdecl f(this, arg1..argN) calling __thiscall target'''
    code = b'\x55\x89\xe5'
    for i in reversed(range(nargs)):
        code += b'\xff\x75' + bytes([12 + 4 * i])
    code += b'\x8b\x4d\x08' + b'\xb8' + _u32(target) + b'\xff\xd0'
    code += b'\x89\xec\x5d\xc3'
    return code


def bytes_ok(addr, start):
    '''the game's code at addr starts with these bytes (hex): the version Lootr knows'''
    return bytes(ffi.buffer(ffi.cast('char *', addr), len(start) // 2)).hex() == start


# keys whose SDL keycode is a character, not scancode | 1 << 30
CHAR_KEYS = {'space': 32, 'return': 13, 'enter': 13, 'tab': 9, 'backspace': 8,
             'escape': 27, 'delete': 127}


def keycode(name):
    '''SDL key name ("A", "Space", "Left", "Keypad 0") -> SDL keycode, 0 if unknown'''
    name = name.strip()
    if len(name) == 1:
        return ord(name.lower())
    if name.lower() in CHAR_KEYS:
        return CHAR_KEYS[name.lower()]
    sc = lib.SDL_GetScancodeFromName(name.encode())
    return sc | (1 << 30) if sc else 0


def func_ok(name):
    addr, start = FUNCS[name]
    return bytes(ffi.buffer(ffi.cast('char *', addr), len(start) // 2)).hex() == start


class Native(object):
    '''the game's UI classes, called from python (thiscall wrapped as cdecl)'''
    def __init__(self):
        self.mem = ExecMemory()

        def tc(name, n, sig):
            return ffi.cast(sig, self.mem.put(thunk_cdecl_to_thiscall(FUNCS[name][0], n)))
        self.new = ffi.cast('void *(*)(unsigned int)', FUNCS['new'][0])
        self.free = ffi.cast('void(*)(void *)', FUNCS['delete'][0])
        self.string_ = tc('string', 2, 'void(*)(void *, char *, void *)')
        self.options_dialog = tc('optionsDialog', 3, 'void(*)(void *, char *, int, int)')
        self.checkbox_line = tc('checkboxLine', 1, 'void(*)(void *, char *)')
        self.dropdown_line = tc('dropdownLine', 4, 'void(*)(void *, char *, char *, void *, int)')
        self.dropdown_ = tc('dropdown', 5, 'void(*)(void *, int, int, char *, void *, int)')
        self.label_ = tc('label', 7, 'void(*)(void *, char *, char *, int, uint32_t, int, uint32_t, int)')
        self.add = tc('addChild', 1, 'void(*)(void *, void *)')
        self.delete_child = tc('deleteChild', 1, 'void(*)(void *, void *)')
        self.set_current = tc('setCurrent', 1, 'void(*)(void *, void *)')
        self.set_text = tc('setText', 1, 'void(*)(void *, char *)')
        self.set_color = tc('setColor', 1, 'void(*)(void *, uint32_t)')

        # a Dropdown does not change itself when an option is clicked: its popup calls the
        # Dropdown's change Handler<std::string> (+0x2c) with the option, and the owner sets
        # it (GraphicsOptions::handleResolutionChange calls Dropdown::setCurrent). Ours is a
        # std::function<void(std::string)> whose storage[0] is the Dropdown.
        def manager(dest, src, op):
            d, s = ffi.cast('uintptr_t *', dest), ffi.cast('uintptr_t *', src)
            if op == 0:
                d[0] = 0
            elif op == 1:
                d[0] = int(ffi.cast('uintptr_t', src))
            elif op == 2:
                d[0], d[1] = s[0], s[1]
            return False

        def changed(data, string):      # string: pointer to the chosen std::string
            try:
                # setCurrent takes the text (const char *), which is the std::string's one
                # word (GCC COW string), as handleResolutionChange passes it: mov eax,[eax]
                text = ffi.cast('void **', string)[0]
                self.set_current(ffi.cast('void *', ffi.cast('uintptr_t *', data)[0]), text)
            except Exception:
                logging.exception('lootr: dropdown change failed')

        self.dd_manager = ffi.callback('bool(*)(void *, void *, int)', manager)
        self.dd_changed = ffi.callback('void(*)(void *, void *)', changed)
        self.keep = []      # C strings / string arrays the game may keep pointers to

        # a DialogButton's click Handler<> (+0x2c) runs std::function<void()>s; ours has the
        # button in storage[0] and calls the Python function registered for it
        self.dialog_button = tc('dialogButton', 4, 'void(*)(void *, char *, char *, int, int)')
        self.on_click = {}      # button address -> function

        def clicked(data):
            try:
                fn = self.on_click.get(int(ffi.cast('uintptr_t *', data)[0]))
                if fn is not None:
                    fn()
            except Exception:
                logging.exception('lootr: button click failed')

        self.btn_clicked = ffi.callback('void(*)(void *)', clicked)
        self.dialog_ = tc('dialog', 4, 'void(*)(void *, char *, char *, char *, char *)')
        # loot sprites: TextureManager::findImage(vid) -> Image {Visual (vptr, type, vid),
        # sheet +0xc, rp (anchor) +0x10, src {x, y, w, h} +0x18}, drawn by Image::draw
        # with XDL_DrawTexture(sheet, src, x - rp.x, y - rp.y, src w, src h, ...)
        self.tm_get = ffi.cast('void *(*)(void)', FUNCS['tmGet'][0])
        self.tm_find = tc('tmFind', 1, 'void *(*)(void *, char *)')
        self.draw_obj_visual = tc('drawObjVisual', 1, 'bool(*)(void *, void *)')
        self.item_lib_get = ffi.cast('void *(*)(void)', FUNCS['itemLibGet'][0])
        self.item_lookup = tc('itemLookup', 1, 'void *(*)(void *, unsigned int)')
        self.lootvids = {}      # item type -> its lootvid (as Loot::Loot looks it up) or None
        self.loot_ctor = tc('lootCtor', 5, 'void(*)(void *, void *, unsigned int, void *, void *, int)')
        self.props_ctor = tc('propsCtor', 0, 'void(*)(void *)')
        self.get_item = tc('getItem', 1, 'void *(*)(void *, int)')
        self.images = {}        # vid -> sprite (see image()) or None

    def image(self, vid):
        '''the sprite of a vid, as the game draws it: {'w', 'h', 'parts': [(sheet, sx, sy,
        sw, sh, x, y, w, h, alpha, blend, flip)]} with x, y from its top left, or None.
        Visuals (vptr, type
        +4): IMAGE 0 (sheet +0xc, src {x, y, w, h} +0x18), VISUAL_SET 3 (pairs (id,
        Visual *): the first is used), ANIMATED_IMAGE 4 (its first animation's first
        frame: FrameElements with sheet, src, size, offset)'''
        if vid in self.images:
            return self.images[vid]
        sprite, kinds = None, []
        tm = self.tm_get()
        v = self.tm_find(tm, self.cstr(vid)) if tm != ffi.NULL and vid else ffi.NULL
        for _ in range(4):
            if v == ffi.NULL:
                break
            kind = ffi.cast('uint8_t *', v)[4]
            kinds.append(int(kind))
            parts = []
            if kind == 0:
                u = ffi.cast('int32_t *', v)
                parts = [(int(ffi.cast('uint32_t *', v)[3]), u[6], u[7], u[8], u[9], 0, 0, u[8], u[9],
                          255, 1, 0)]
            elif kind == 3:
                vec = ffi.cast('struct VisualSet *', v).visuals
                pairs = ffi.cast('uint32_t *', vec.begin)
                v = ffi.cast('void *', pairs[1]) if vec.begin != vec.end else ffi.NULL
                continue
            elif kind == 4:
                anims = util.vec2list(ffi.cast('struct AnimatedImage *', v).anims, 'struct Animation *')
                frames = util.vec2list(anims[0].frames, 'struct Frame *') if anims else []
                els = util.vec2list(frames[0].elements, 'struct FrameElement *') if frames else []
                # as FrameElement::draw: opacity 0..255, its own blend mode, flips
                parts = [(int(e.sheet), e.src.x, e.src.y, e.src.w, e.src.h,
                          e.offset.x, e.offset.y, e.size.x, e.size.y,
                          max(0, min(255, e.opacity)), int(e.blendMode),
                          (1 if e.flipH else 0) | (2 if e.flipV else 0)) for e in els]
            parts = [q for q in parts if q[3] > 0 and q[4] > 0 and q[7] > 0 and q[8] > 0]
            if parts:
                x0, y0 = min(q[5] for q in parts), min(q[6] for q in parts)
                x1, y1 = max(q[5] + q[7] for q in parts), max(q[6] + q[8] for q in parts)
                sprite = {'w': x1 - x0, 'h': y1 - y0, 'parts': [
                    q[:5] + (q[5] - x0, q[6] - y0) + q[7:] for q in parts]}
            break
        self.images[vid] = sprite
        return sprite

    def lootvid(self, t):
        '''the loot sprite name of an item type: ItemLibrary::lookup(type)->lootvid'''
        if t not in self.lootvids:
            vid = None
            lib_ = self.item_lib_get()
            desc = self.item_lookup(lib_, t) if lib_ != ffi.NULL else ffi.NULL
            if desc != ffi.NULL:
                d = ffi.cast('struct ItemDescription *', desc)
                if d.lootvid != ffi.NULL:
                    vid = util.getstr(d.lootvid)
                    if not vid or vid == '(NULL)':
                        vid = None
            self.lootvids[t] = vid
        return self.lootvids[t]

    def make_loot(self, subworld, item_props):
        '''a Loot object built by the game's own Loot::Loot (as Chest::throwLoot builds the
        items it throws) but never added to the world: only drawn. Never freed (one per item
        type per sub-world).'''
        props = self.new(0x100)             # Properties (throwLoot keeps one on its stack)
        ffi.memmove(props, b'\0' * 0x100, 0x100)
        self.props_ctor(props)
        loot = self.new(0x168)              # sizeof(Loot), as throwLoot allocates
        self.loot_ctor(loot, subworld, 0x7ffff000, props, item_props, 0)
        return ffi.cast('struct WorldObject *', loot)

    def button(self, parent, text, ident, x, y, fn, w=BUTTON_W, h=BUTTON_H):
        '''a DialogButton (as Done / Reset To Defaults) that calls fn when clicked'''
        b = self.new(0x80)      # DialogButton is 0x48 bytes
        self.dialog_button(b, self.cstr(text), self.cstr(ident), w, h)
        e = ffi.cast('struct UIElement *', b)
        e.x, e.y = x, y
        a = int(ffi.cast('uintptr_t', b))
        self.on_handler(a, BUTTON_CLICK, fn)
        self.add(parent, b)
        return a

    def on_handler(self, obj, offset, fn):
        '''add fn to the Handler<> (std::function<void()> list) at obj + offset'''
        key = obj + offset      # storage[0]: what clicked() looks fn up by
        self.add_handler(obj, offset, int(ffi.cast('uintptr_t', self.dd_manager)),
                         int(ffi.cast('uintptr_t', self.btn_clicked)), (key, 0))
        self.on_click[key] = fn

    def confirm(self, parent, title, message, ok, cancel, on_ok):
        '''the game's yes / no box (as "Area not safe ... Exit Anyway / Cancel"), a child of
        parent: Cancel / Esc remove it; OK calls on_ok (which must remove it)'''
        d = self.new(0x80)      # Dialog is 0x64 bytes
        self.dialog_(d, self.cstr(title), self.cstr(message), self.cstr(ok), self.cstr(cancel))
        a = int(ffi.cast('uintptr_t', d))
        fn = ffi.cast('uint32_t *', self.new(0x10))
        fn[0], fn[1], fn[2], fn[3] = FUNCS['deleteChild'][0], 0, a, int(ffi.cast('uintptr_t', parent))
        self.add_handler(a, CONFIRM_CANCEL, FUNCS['cancelManager'][0], FUNCS['cancelInvoker'][0],
                         (int(ffi.cast('uintptr_t', fn)), 0))
        self.on_handler(a, CONFIRM_OK, on_ok)
        self.add(parent, d)
        return a

    def on_change(self, dropdown):
        '''make the Dropdown show the option that is clicked'''
        self.add_handler(int(ffi.cast('uintptr_t', dropdown)), DROPDOWN_CHANGE,
                         int(ffi.cast('uintptr_t', self.dd_manager)),
                         int(ffi.cast('uintptr_t', self.dd_changed)),
                         (int(ffi.cast('uintptr_t', dropdown)), 0))

    def cstr(self, s):
        c = ffi.new('char[]', s.encode('utf-8') if isinstance(s, str) else s)
        self.keep.append(c)
        return c

    def strings(self, items):
        '''a C array of std::string (the game copies them)'''
        arr = ffi.new('void *[]', max(1, len(items)))
        alloc = ffi.new('char[4]')
        for i, s in enumerate(items):
            self.string_(ffi.cast('void *', arr + i), self.cstr(s), alloc)
        self.keep.append(arr)
        return arr

    def container(self, x, y, w, h):
        p = ffi.cast('uint32_t *', self.new(0x2c))
        for i, v in enumerate([CONTAINER_VT, 0, 0, 1, x, y, w, h, 0, 0, 0]):
            p[i] = v & 0xffffffff
        return p

    def label(self, parent, text, x, y, size=15, color=WHITE, font=b'TenbyFive'):
        lb = self.new(0x54)
        self.label_(lb, self.cstr(text), self.cstr(font), size, color, 1, BLACK, 0)
        e = ffi.cast('struct UIElement *', lb)
        e.x, e.y = x, y
        self.add(parent, lb)
        return lb

    def dropdown(self, parent, x, w, current, options, y=None):
        dd = self.new(0x4c)
        self.dropdown_(dd, w, DD_H, self.cstr(current), self.strings(options), len(options))
        e = ffi.cast('struct UIElement *', dd)
        e.x, e.y = x, (12 - e.h // 2) if y is None else y     # default: centred on a 24 px line
        self.add(parent, dd)
        return dd

    def add_handler(self, obj_addr, offset, manager, invoker, storage):
        '''append a std::function<void()> to a Handler<> at obj+offset (as the game's
        inlined Handler::add does): id = counter, then counter + 1'''
        base = ffi.cast('uint32_t *', obj_addr + offset)
        counter, begin, end, cap = base[0], base[1], base[2], base[3]
        if end == cap:
            n = (end - begin) // HANDLER_ENTRY
            new = int(ffi.cast('uintptr_t', self.new((n + 4) * HANDLER_ENTRY)))
            if n:
                ffi.memmove(ffi.cast('void *', new), ffi.cast('void *', begin), n * HANDLER_ENTRY)
                self.free(ffi.cast('void *', begin))
            begin, end, cap = new, new + n * HANDLER_ENTRY, new + (n + 4) * HANDLER_ENTRY
        e = ffi.cast('uint32_t *', end)
        e[0], e[1], e[2], e[3], e[4] = counter, storage[0], storage[1], manager, invoker
        base[0], base[1], base[2], base[3] = counter + 1, begin, end + HANDLER_ENTRY, cap


def _children(cont):
    return [int(ffi.cast('uintptr_t', c)) for c in
            util.vec2list(ffi.cast('struct UIElementContainer *', cont).children, 'struct UIElement *')]


def label_text(lbl_addr):
    return ffi.string(ffi.cast('struct Label *', lbl_addr).text.s).decode('utf-8', 'replace')


# Esc menu button ############################################################
# GameMenu::refresh builds the Esc menu with GameMenu::addButton(label, std::function).
# faction.py hooks addButton to put FACTION before "Exit Game". Hooking the same function
# twice is not safe, so when faction's hook is there Lootr chains through it (it wraps
# faction's st['orig']); only without faction does Lootr hook addButton itself.

EXIT_LABEL = b'Exit Game'
ADD_BUTTON = (0x4957f0, '5589e557565381ecac00')     # GameMenu::addButton (unhooked bytes)
FACTION_WAIT = 15.0     # seconds to wait for faction.py's hook before hooking ourselves


def _addr(p):
    return int(ffi.cast('uintptr_t', p))


def _screen_pos(el):
    '''an element's x, y on the screen (UI pixels): its own plus all its parents' '''
    e = ffi.cast('struct UIElement *', el)
    x = y = 0
    for _ in range(32):
        x, y = x + e.x, y + e.y
        if e.parent == ffi.NULL:
            break
        e = ffi.cast('struct UIElement *', e.parent)
    return x, y


def install_menu(refs, allow_own):
    '''add the LOOTR button to the Esc menu once per game session (state in refs, so it
    survives reloads). Pressing it calls st['open'](GameMenu), which the plugin sets.
    returns the state, or None if it should be tried again later'''
    st = refs.get('lootrMenuHook')
    if st is not None:
        return st
    fst = refs.get('factionMenuHook')
    chain = fst is not None and fst.get('ok')
    if not chain and not allow_own:
        return None
    st = {'ok': False, 'label': b'Lootr', 'enabled': True, 'open': None, 'errors': 0,
          'mode': 'faction' if chain else 'own', 'v': 2}
    refs['lootrMenuHook'] = st
    try:
        mem = ExecMemory()

        # std::function<void()> (libstdc++: 8 bytes storage, manager, invoker); storage[0] = GameMenu
        def manager(dest, src, op):
            d, s = ffi.cast('uintptr_t *', dest), ffi.cast('uintptr_t *', src)
            if op == 0:
                d[0] = 0
            elif op == 1:
                d[0] = _addr(src)
            elif op == 2:
                d[0], d[1] = s[0], s[1]
            return False

        def invoke(data):
            try:   # like the Controls button: the window opens inside the Esc menu
                gm = ffi.cast('uintptr_t *', data)[0]
                if st['open'] is not None:
                    st['open'](gm)
            except Exception:
                st['errors'] += 1
                if st['errors'] <= 3:
                    logging.exception('lootr: opening the window failed')

        man_cb = ffi.callback('bool(*)(void *, void *, int)', manager)
        inv_cb = ffi.callback('void(*)(void *)', invoke)

        def add_ours(real, this, label):
            try:
                if (st['enabled'] and label != ffi.NULL and ffi.string(label) == EXIT_LABEL
                        and ffi.cast('struct GameMenu *', this).gameClient != ffi.NULL):
                    f = ffi.new('uintptr_t[4]', [_addr(this), 0, _addr(man_cb), _addr(inv_cb)])
                    st['lbl'] = ffi.new('char[]', st['label'])
                    real(this, st['lbl'], f)
            except Exception:
                st['errors'] += 1
                if st['errors'] <= 3:
                    logging.exception('lootr: adding the button failed')

        if chain:
            real = fst['orig']

            def chained(this, label, fn):
                add_ours(real, this, label)
                real(this, label, fn)
            fst['orig'] = chained       # faction calls st['orig'] for every button it passes on
            st['keep'] = (mem, man_cb, inv_cb, chained, real)
            st['ok'] = True
            return st

        holder = {}

        def add_button(this, label, fn):
            add_ours(holder['orig'], this, label)
            holder['orig'](this, label, fn)

        if not bytes_ok(*ADD_BUTTON):
            raise RuntimeError('GameMenu::addButton is not the code Lootr knows (game updated, '
                               'or another plugin hooks it)')
        cb = ffi.callback('void(*)(void *, char *, void *)', add_button)
        entry = mem.put(thunk_thiscall_to_cdecl(_addr(cb), 2))
        hook = lib.subhook_new(ffi.cast('void *', ADD_BUTTON[0]), ffi.cast('void *', entry), 0)
        tramp = lib.subhook_get_trampoline(hook)
        if tramp == ffi.NULL:
            raise RuntimeError('no trampoline for GameMenu::addButton')
        holder['orig'] = ffi.cast('void(*)(void *, char *, void *)', mem.put(
            thunk_cdecl_to_thiscall(_addr(tramp), 2)))
        st['keep'] = (mem, man_cb, inv_cb, cb, hook, holder)
        lib.subhook_install(hook)
        st['ok'] = bool(lib.subhook_is_installed(hook))
        if not st['ok']:
            logging.error('lootr: Esc menu hook install failed')
    except Exception:
        logging.exception('lootr: Esc menu setup failed')
    return st


# Other plugins' drawing ######################################################
# Plugins draw in onPresent, after the game has drawn its menus, so their text and boxes
# land on top of the Lootr window. While it is open, SBPE's drawing functions are swapped
# for do-nothing ones around the onPresent callbacks: plugins keep running, they just
# draw nothing over the window. Installed once per game session (state in refs).

DRAW_FUNCS = ('XDL_FillRect', 'XDL_FillTri', 'XDL_DrawTexture', 'XDL_DrawRect',
              'XDL_DrawLine', 'XDL_DrawFromNumberDict')


def _draw_nothing(*args):
    return 0


def install_draw_gate(refs):
    '''wrap the plugin manager's runCallbacks; returns the shared state'''
    st = refs.get('lootrDrawGate')
    if st is not None:
        return st
    st = {'open': None}
    mgr = refs.manager
    orig = mgr.runCallbacks

    def gated(cbname, *args):
        hide = False
        if cbname == 'onPresent' and st['open'] is not None:
            fn = st['open']()       # weak ref to the plugin's windowOpen (None once it is gone)
            try:
                hide = fn is not None and fn()
            except Exception:
                hide = False
        if not hide:
            return orig(cbname, *args)
        saved = {k: refs.get(k) for k in DRAW_FUNCS if refs.get(k) is not None}
        for k in saved:
            refs[k] = _draw_nothing
        try:
            return orig(cbname, *args)
        finally:
            for k, v in saved.items():
                refs[k] = v

    mgr.runCallbacks = gated
    st['orig'] = orig
    refs['lootrDrawGate'] = st
    return st


# settings ###################################################################

DEFAULTS = {
    'enabled': False,       # auto loot on/off
    'notify': True,         # show a message when an item is picked up
    'highlight': False,     # box around wanted items on the ground
    'magnify': False,       # enlarged sprite above wanted items on the ground
    'highlight_inv': False,  # box around wanted items in the inventory, stash and HUD (inventory open)
    'chest_contents': False,    # enlarged sprites above chests: wanted items, HP (if hurt), only-EC
    'item': None,           # chosen item type id
    'class': 1,             # Class dropdown (CHAR_NAMES id)
    'slot': 256,            # Slot dropdown (SLOT_NAMES id)
    'rules': {},            # {item id: {mod count: {stat id: 1 (check) | -1 (X)}}}, as strings
}
SLOT_FILTERS = [('Main', 256), ('Secondary', 512), ('Special', 768), ('Armor', 1024),
                ('Mobility', 1280), ('Implant', 1536)]
CLASS_FILTERS = [(n, c) for c, n in sorted(CHAR_NAMES.items())]
PREV_PAGE, NEXT_PAGE = '< Previous', 'More >'
CHECKBOXES = [              # Lootr Settings window: (setting, row text)
    ('enabled', 'Auto Loot'),
    ('notify', 'Message On Pickup'),
    ('highlight', 'Highlight Items'),
    ('magnify', 'Magnify Items'),
    ('highlight_inv', 'Highlight Items In Inventory'),
    ('chest_contents', 'Show Chest Contents'),
]
BETA = ('chest_contents',)  # settings shown with a BETA tag
OLD_SETTINGS = ('pickup_all', 'my_class', 'max_distance', 'hp_chests')     # removed; dropped on load


class Plugin(PluginBase):
    def onInit(self):
        self.config.option('label', 'Lootr', 'str')
        self.config.option('interact_key', INTERACT_KEY, 'str')     # your in-game interact key
        self.path = os.path.join(self.refs.SCRIPTPATH, 'lootr_settings.json')
        self.settings = dict(DEFAULTS)
        try:
            with open(self.path) as f:
                self.settings.update(json.load(f))
        except Exception:
            pass
        if self.settings.get('hp_chests'):     # Highlight HP Chests became Show Chest Contents
            self.settings['chest_contents'] = True
        for k in OLD_SETTINGS:
            self.settings.pop(k, None)
        rules = self.settings.get('rules', {})
        for item, cols in list(rules.items()):
            stock = cols.get('0')   # Stock used to have cells: a check there is now ANY Stock
            if stock and ANY not in stock:
                if 1 in stock.values() and -1 not in stock.values():
                    cols['0'] = {ANY: 1}
                else:
                    cols.pop('0')
            if not cols:
                rules.pop(item)
        self.items = ITEMS
        self.page = 0
        self.lootClass = None   # vtable of the game's Loot class (found by name once)
        self.chestClass = None  # ... and of its Chest class
        self.chestOk = None     # WorldView layout checked (Show Chest Contents)
        self.chestFailed = False    # Show Chest Contents hit an error: off until reload
        self.chestLoot = {}     # (sub-world, item type) -> a Loot built to draw it (Native.make_loot)
        self.drawFailed = False     # Highlight / Magnify hit an error: off until reload
        self.offsetOk = None        # WorldView layout checked (Magnify)
        self.invClass = None        # vtable of the game's InventoryOverlay (found by name once)
        self.pressed = {}           # Auto Loot: (world id, obj id) -> (time pressed, item name)
        self.fullT = -FULL_EVERY    # last "Inventory Full" message
        self.keyDown = None         # (keycode, time to release) of Auto Loot's interact press
        self.keyFn = None           # how keys reach the game (sendKey / keyboardCallback)
        self.keyLogged = False
        self.mouse = None           # SDL mouse polling (pollMouse), set up on first use
        # SBPE's mouse patch (onMouseButton callbacks) puts clickConsumed in refs; without
        # it Lootr reads clicks itself, and never writes clickConsumed there
        self.mousePatch = 'clickConsumed' in self.refs
        self.gate = None
        try:
            self.gate = install_draw_gate(self.refs)
            self.gate['open'] = weakref.WeakMethod(self.windowOpen)    # never keeps us alive
            self.gate['owner'] = id(self)
        except Exception:
            logging.exception('lootr: could not hide other plugins over the Lootr window')
        self.lootFailed = False     # Auto Loot hit an error: off until the plugin reloads
        self.mine = set()           # ObjKeys of loot you dropped from your inventory
        self.ownItems = None        # last frame's inventory: {signature: count}
        self.lootKeys = None        # last frame's loot ObjKeys
        self.dropped = []           # (time, signature) of items that left your inventory
        self.newLoot = []           # (time, key, signature) of loot that appeared near you
        self.dropFailed = False
        self.messages = []          # floating messages: (time, text, color)
        self.msgText = None
        if self.settings.get('class') not in CHAR_NAMES:
            self.settings['class'] = 1
        if self.settings.get('slot') not in [v for _, v in SLOT_FILTERS]:
            self.settings['slot'] = 256
        if not isinstance(self.settings.get('rules'), dict):
            self.settings['rules'] = {}
        self.win = None         # the open Lootr dialog: addresses of it and its widgets
        self.started = time.perf_counter()
        self.ok = all(func_ok(n) for n in FUNCS)
        if not self.ok:
            logging.error('lootr: game functions not found (game updated?), the Lootr window is off')
        keep = self.refs.setdefault('lootrNative', {})
        if self.ok and (keep.get('native') is None or keep.get('v') != NATIVE_VERSION):
            keep['native'], keep['v'] = Native(), NATIVE_VERSION
        self.n = self.refs['lootrNative'].get('native')
        self.st = None
        self.tryMenu()

    # Esc menu ###############################################################

    def tryMenu(self):
        if self.st is not None:
            return
        # faction.py is loaded first (file order) when it is enabled; give it time to hook,
        # so the game function is only ever hooked once
        faction_on = (self.refs.config.getboolean('plugin_faction', 'enabled', fallback=True)
                      and os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'faction.py')))
        waited = time.perf_counter() - self.started > FACTION_WAIT
        st = install_menu(self.refs, allow_own=not faction_on or waited)
        if st is None:
            return
        self.st = st
        if st.get('v') != 2:
            # the Esc button was made by the earlier Lootr (drawn window) this game session;
            # its button closes the menu instead of calling st['open']
            logging.warning('lootr: restart the game once to get the new Lootr window')
        st['enabled'] = self.ok
        st['owner'] = id(self)
        st['open'] = self.openWindow

    # Auto Loot ##############################################################

    def beforeUpdate(self):
        '''Auto Loot: read the item you stand on (Player.interactObj: the game's own interact
        target, the overlapping item Player::doActivates picks each step) and press interact
        when the table wants it. Done before the game's update, so this frame's world steps
        (and the PLAYER_INPUT the server gets) already have the press.'''
        if self.mouse is not False:
            try:
                self.pollMouse()
            except Exception:
                logging.exception('lootr: reading the mouse failed, table clicks are off')
                self.mouse = False
        if not self.settings.get('enabled') or self.n is None or self.lootFailed:
            return
        try:
            self.autoLoot()
        except Exception:
            logging.exception('lootr: auto loot failed, Auto Loot is off until the plugin reloads')
            self.lootFailed = True

    def autoLoot(self):
        cw, wc = self.refs.ClientWorld, self.refs.WorldClient
        if cw == ffi.NULL or wc == ffi.NULL or cw.player == ffi.NULL:
            return
        if lib is not None and lib.SDL_IsTextInputActive():
            return              # typing in chat
        key = cw.player.interactObj
        key = (int(key.worldId), int(key.objId))
        if key[1] == 0:
            return
        if key in self.mine:
            return              # you dropped it: never auto looted
        o = self.lootObjects().get(key)
        if o is None:
            return              # not loot (a door, portal, NPC...): never pressed
        t, stats = self.lootItem(o)
        if not wants(self.settings['rules'], t, stats):
            return
        pc = self.pc()
        if pc is None:
            return
        now = time.perf_counter()
        if self.bagFull(pc):
            if now - self.fullT >= FULL_EVERY:
                self.fullT = now
                self.message('Inventory Full', MSG_RED)
            return
        last = self.pressed.get(key)
        if last is not None and now - last[0] < PICK_RETRY:
            return
        if not self.holdKey(self.config.interact_key, PICK_HOLD):
            return
        self.pressed[key] = (now, self.itemName(t, stats))

    def sendKey(self, down, code):
        '''a key event for the game, as if from the keyboard: SBPE's refs.sendKey when it
        has the keyboard patch, else the game's keyboardCallback with SBPE's userData'''
        if self.keyFn is None:
            send = getattr(self.refs, 'sendKey', None)
            if send is not None:
                self.keyFn = send
            elif bytes_ok(*KEYBOARD_CB):
                cb = ffi.cast('void(*)(int, int, void *)', KEYBOARD_CB[0])

                def direct(d, c):
                    ud = self.refs.userData_[0] if self.refs.userData_ is not None else ffi.NULL
                    if ud != ffi.NULL:      # the game's input object: none yet = drop it
                        cb(d, c, ud)
                self.keyFn = direct
            else:
                self.keyFn = False
                logging.error('lootr: keyboardCallback is not the code Lootr knows (game '
                              'updated?), Auto Loot cannot press interact')
        if self.keyFn:
            self.keyFn(down, code)
        return bool(self.keyFn)

    def holdKey(self, name, seconds):
        '''press a key now, released after seconds (in afterUpdate)'''
        k = keycode(name or INTERACT_KEY)
        if not k:
            if not self.keyLogged:
                self.keyLogged = True
                logging.error('lootr: unknown interact_key %r', name)
            return False
        if not self.sendKey(1, k):
            return False
        self.keyDown = (k, time.perf_counter() + seconds)
        return True

    def releaseKey(self, force=False):
        if self.keyDown is not None and (force or time.perf_counter() >= self.keyDown[1]):
            k, self.keyDown = self.keyDown[0], None
            self.sendKey(0, k)

    def pc(self):
        '''ClientWorld.player, only once it really is a built PlayerCharacter (else None).
        Right after a map loads it can be some other object; PlayerCharacter::getItem on
        that reads garbage as the item hash table and crashes the game (divide by zero /
        access violation in _Hashtable::find) -- same check as crit.player().'''
        cw = self.refs.ClientWorld
        if cw == ffi.NULL or cw.player == ffi.NULL:
            return None
        if util.getClassName(cw.player) not in self.refs.CASTABLE['PlayerCharacter']:
            return None
        return cw.player

    def bagFull(self, pc):
        '''no empty backpack slot (PlayerCharacter::getItem gives NULL for an empty one)'''
        return all(self.n.get_item(pc, s) != ffi.NULL for s in BAG_SLOTS)

    def checkPicked(self):
        '''a pressed item that is gone from the world was picked up: the green message'''
        if not self.pressed:
            return
        now = time.perf_counter()
        live = self.lootObjects()
        for key, (t, name) in list(self.pressed.items()):
            if key not in live:
                del self.pressed[key]
                if now - t <= PICK_CONFIRM and self.settings.get('notify'):
                    self.message('+ ' + name, MSG_GREEN)
            elif now - t > PICK_CONFIRM:
                del self.pressed[key]

    def message(self, text, color):
        '''a message above your character that floats up and fades'''
        self.messages.append((time.perf_counter(), text, color))
        self.messages = self.messages[-6:]

    def drawMessages(self):
        if not self.messages:
            return
        now = time.perf_counter()
        self.messages = [m for m in self.messages if now - m[0] < MSG_TIME]
        cw, wv = self.refs.ClientWorld, self.refs.WorldView
        if not self.messages or cw == ffi.NULL or cw.player == ffi.NULL or wv == ffi.NULL:
            return
        p = ffi.cast('struct WorldObject *', cw.player).props
        x = (p.xmp + p.wmp // 2) / 256.0 - wv.offset.x
        y = p.ymp / 256.0 - wv.offset.y - 8
        if self.msgText is None:
            self.msgText = util.PlainText(font=b'HemiHeadBold', size=MSG_SIZE, screenCoords=False)
        txt = self.msgText
        for i, (t0, text, color) in enumerate(reversed(self.messages)):
            age = (now - t0) / MSG_TIME
            txt.text = text
            txt.color = color
            txt.alpha = 1.0 if age < 0.5 else max(0.0, 1.0 - (age - 0.5) / 0.5)
            txt.draw(x, y - age * MSG_RISE - i * (MSG_SIZE + 2), anchorX=0.5, anchorY=1)

    def afterUpdate(self):
        try:
            self.releaseKey()
        except Exception:
            logging.exception('lootr: releasing the interact key failed')
            self.keyDown = None
        try:
            self.checkPicked()
        except Exception:
            logging.exception('lootr: pickup check failed')
            self.pressed = {}
        if not self.dropFailed:
            try:
                self.trackDrops()
            except Exception:
                logging.exception('lootr: tracking your drops failed (off until reload)')
                self.dropFailed = True
        self.tryMenu()
        if self.st is not None:
            self.st['label'] = (self.config.label or 'Lootr').encode()
        if self.win is None:
            return
        try:
            if not self.alive():
                self.win = None
                return
            self.pollSettings()
            win = self.win
            if win.get('confirm') is not None and win['confirm'] not in _children(win['dlg']):
                win['confirm'] = None           # Cancel / Esc closed it
            if win.pop('doReset', False):
                self.doReset()
            if win.pop('askReset', False):
                self.askReset()
            if win.pop('openSettings', False):
                self.openSettings()
            self.poll()
        except Exception:
            logging.exception('lootr: window update failed')
            self.win = None

    def save(self):
        try:
            tmp = self.path + '.tmp'
            with open(tmp, 'w') as f:
                json.dump(self.settings, f, indent=1, sort_keys=True)
            try:
                os.replace(tmp, self.path)
            except PermissionError:     # Windows: the file is open elsewhere (scanner, editor)
                with open(self.path, 'w') as f:
                    json.dump(self.settings, f, indent=1, sort_keys=True)
        except Exception:
            logging.exception('lootr: could not save %s', self.path)

    # the window #############################################################

    def openWindow(self, gm):
        '''the LOOTR button: an OptionsDialog added to the Esc menu, as GameMenu::controls does.
        Top left: Class, Slot and Item dropdowns; right of them a table like the Controls
        page: a column per mod count (Stock .. Prototype), a row per mod the item can roll,
        and cells that cycle -- / check / X when clicked.'''
        n = self.n
        if n is None:
            return
        if self.win is not None and self.alive():
            return              # already open
        sw, sh, ox, oy = self.screen(gm)
        dd_end = MARGIN + sum(w for _, w in DD_W) + DD_GAP * (len(DD_W) - 1)
        tx = dd_end + TABLE_GAP
        rows = max([len(matrix_rows(t)) for t in self.items] + [1])
        need_w = tx + NAME_W + len(COLUMNS) * COL_MIN + MARGIN
        need_h = TOP_Y + ROW_H * (rows + 1) + 110       # room for Done / Reset To Defaults
        # most of the screen; Done / Reset To Defaults go along the bottom from its size
        w = max(DIALOG_W, need_w, int(sw * DIALOG_FILL))
        h = max(need_h, int(sh * DIALOG_FILL))
        dlg = n.new(0x80)       # OptionsDialog is 0x58 bytes (GameplayOptions adds 4 to it)
        n.options_dialog(dlg, n.cstr(b'Lootr'), w, h)
        d = _addr(dlg)
        col_w = max(COL_MIN, min(COL_MAX, (w - MARGIN - tx - NAME_W) // len(COLUMNS)))
        self.win = win = {'gm': gm, 'dlg': d, 'tx': tx, 'colW': col_w, 'dd': {}}

        # the three dropdowns, each with an orange header above it (as the table's)
        x = MARGIN
        for key, dw in DD_W:
            n.label(dlg, key.capitalize(), x, TOP_Y, color=ORANGE)
            win['dd'][key] = {'x': x, 'w': dw}
            x += dw + DD_GAP
        cls = self.settings['class']
        win['class'] = self.dropdown('class', CHAR_NAMES[cls], [nm for nm, _ in CLASS_FILTERS])
        win['slot'] = self.dropdown('slot', SLOT_NAMES[self.settings['slot']], [nm for nm, _ in SLOT_FILTERS])
        self.page = None        # itemDropdown: the page holding the chosen item
        self.itemDropdown()

        # Done / Esc fire the dialog's close handler: remove it from the Esc menu (as Controls)
        fn = ffi.cast('uint32_t *', n.new(0x10))
        fn[0], fn[1], fn[2], fn[3] = FUNCS['deleteChild'][0], 0, d, gm
        n.add_handler(d, DIALOG_CLOSE, FUNCS['closeManager'][0], FUNCS['closeInvoker'][0],
                      (_addr(fn), 0))
        # SETTINGS, between Reset To Defaults and Done: OptionsDialog puts those at a
        # quarter and three quarters of (w - 100), + 60, and h - 50 - their height
        n.button(dlg, b'Settings', b'Lootr / Settings', (w - 100) // 2 + 60 - BUTTON_W // 2,
                 h - 50 - BUTTON_H, self.wantSettings)
        self.hookReset(d)
        n.add(ffi.cast('void *', gm), dlg)
        # addChild centres it on the Esc menu, which is smaller than the screen: centre it
        # on the screen instead (x / y are relative to the Esc menu)
        e = ffi.cast('struct UIElement *', dlg)
        e.x, e.y = (sw - w) // 2 - ox, (sh - h) // 2 - oy

    # the Lootr Settings window ##############################################

    def wantSettings(self):
        '''SETTINGS clicked: open the window after the game's click handling (afterUpdate)'''
        if self.win is not None:
            self.win['openSettings'] = True

    def openSettings(self):
        '''a second OptionsDialog, a child of the Lootr window (it centres itself on it);
        Done / Esc remove it from the Lootr window again'''
        n, win = self.n, self.win
        if win.get('set') is not None and win['set']['dlg'] in _children(win['dlg']):
            return              # already open
        rows = len(CHECKBOXES)
        h = LINE_Y + rows * (24 + LINE_GAP) + 110
        dlg = n.new(0x80)
        n.options_dialog(dlg, n.cstr(b'Lootr Settings'), DIALOG_W, h)
        d = _addr(dlg)
        st = win['set'] = {'dlg': d, 'checks': {}, 'y': LINE_Y}
        for key, text in CHECKBOXES:
            line = n.new(0x34)
            n.checkbox_line(line, n.cstr(text))
            box = ffi.cast('uint32_t *', _addr(line) + LINE_CHECKBOX)[0]
            ffi.cast('uint8_t *', box + CHECKBOX_ON)[0] = 1 if self.settings[key] else 0
            self.placeRow(st, line)
            st['checks'][key] = box
            if key in BETA:     # a small orange BETA tag right after its name
                name = ffi.cast('struct UIElement *',       # CheckboxLine.name, before its Checkbox
                                ffi.cast('uint32_t *', _addr(line) + LINE_CHECKBOX - 4)[0])
                tag = ffi.cast('struct UIElement *', n.label(line, b'BETA', name.x + name.w + 8, 0,
                                                             size=12, color=ORANGE, font=b'HemiHeadBold'))
                tag.y = name.y + (name.h - tag.h) // 2
        fn = ffi.cast('uint32_t *', n.new(0x10))
        fn[0], fn[1], fn[2], fn[3] = FUNCS['deleteChild'][0], 0, d, win['dlg']
        n.add_handler(d, DIALOG_CLOSE, FUNCS['closeManager'][0], FUNCS['closeInvoker'][0],
                      (_addr(fn), 0))
        self.hookReset(d)
        n.add(ffi.cast('void *', win['dlg']), dlg)

    # Reset To Defaults ######################################################

    def hookReset(self, dlg):
        '''the dialog's Reset To Defaults button (the game's handler does nothing) asks first'''
        btn = ffi.cast('uint32_t *', dlg + RESET_BUTTON)[0]
        if btn:
            self.n.on_handler(btn, BUTTON_CLICK, self.wantReset)

    def wantReset(self):
        if self.win is not None:
            self.win['askReset'] = True

    def askReset(self):
        '''the game's yes / no box, on top of the Lootr window'''
        win = self.win
        if win.get('confirm') is not None and win['confirm'] in _children(win['dlg']):
            return
        win['confirm'] = self.n.confirm(
            ffi.cast('void *', win['dlg']), b'Reset Lootr?',
            b'Are you sure? This resets all Lootr settings and sets every mark in the table '
            b'back to --, for every item.', b'Reset', b'Cancel', self.confirmedReset)

    def confirmedReset(self):
        if self.win is not None:
            self.win['doReset'] = True

    def doReset(self):
        '''settings back to their defaults and every mark to --; the Class / Slot / Item
        choice stays'''
        win, s = self.win, self.settings
        conf = win.pop('confirm', None)
        if conf is not None and conf in _children(win['dlg']):
            self.n.delete_child(ffi.cast('void *', win['dlg']), ffi.cast('void *', conf))
        keep = {k: s[k] for k in ('class', 'slot', 'item')}
        s.clear()
        s.update(DEFAULTS)
        s.update(keep)
        s['rules'] = {}
        self.save()
        self.table()            # every cell back to --
        st = win.get('set')
        if st is not None:      # the settings window shows the defaults too
            for key, box in st['checks'].items():
                ffi.cast('uint8_t *', box + CHECKBOX_ON)[0] = 1 if s[key] else 0

    def placeRow(self, st, line):
        e = ffi.cast('struct UIElement *', line)
        e.x, e.y = LINE_X, st['y']
        st['y'] += e.h + LINE_GAP
        self.n.add(ffi.cast('void *', st['dlg']), line)

    def pollSettings(self):
        '''read the settings window (the game changes its widgets on click); save changes'''
        win, s = self.win, self.settings
        st = win.get('set')
        if st is None:
            return
        if st['dlg'] not in _children(win['dlg']):     # closed (Done / Esc)
            win['set'] = None
            return
        changed = False
        for key, box in st['checks'].items():
            v = bool(ffi.cast('uint8_t *', box + CHECKBOX_ON)[0])
            if v != s[key]:
                s[key], changed = v, True
        if changed:
            self.save()

    def screen(self, gm):
        '''(screen w, h, and the Esc menu's x, y on it): the Stage is the whole game screen'''
        e = ffi.cast('struct UIElement *', gm)
        ox = oy = 0
        el, top = e, e
        for _ in range(16):     # the Esc menu's position on the screen
            ox, oy = ox + el.x, oy + el.y
            top = el
            if el.parent == ffi.NULL:
                break
            el = ffi.cast('struct UIElement *', el.parent)
        sw = sh = 0
        try:
            stage = self.refs.stage[0]
            if stage != ffi.NULL:
                se = ffi.cast('struct UIElement *', stage)
                sw, sh = se.w, se.h
        except Exception:
            pass
        if sw <= 0 or sh <= 0:      # no Stage size: the outermost parent's
            sw, sh = top.w, top.h
            if top is not e:
                ox, oy = ox - top.x, oy - top.y
        return sw, sh, ox, oy

    def dropdown(self, key, current, options):
        '''one of the three top-left dropdowns; returns what poll() needs to read it'''
        win = self.win
        p = win['dd'][key]
        dd = self.n.dropdown(ffi.cast('void *', win['dlg']), p['x'], p['w'], current, options,
                             y=TOP_Y + 26)
        self.n.on_change(dd)
        lbl = ffi.cast('uint32_t *', _addr(dd) + DROPDOWN_LABEL)[0]
        return {'el': _addr(dd), 'label': lbl, 'options': list(options), 'value': current}

    def filtered(self):
        '''items for the Class / Slot choice: ones that class can use, and class-less ones'''
        cls, slot = self.settings['class'], self.settings['slot']
        out = []
        for t, r in self.items.items():
            if r['slot'] != slot:
                continue
            if r['usableby'] and cls not in r['usableby']:
                continue
            out.append((r['name'].lower(), t))
        return [t for _, t in sorted(out)]

    def itemDropdown(self):
        '''the Item dropdown for the Class / Slot choice (rebuilt when they change); long
        lists are paged with Previous / More entries'''
        win, s = self.win, self.settings
        old = win.pop('item', None)
        if old is not None:
            self.n.delete_child(ffi.cast('void *', win['dlg']), ffi.cast('void *', old['el']))
        rows = self.filtered()
        pages = max(1, (len(rows) + ITEM_PAGE - 1) // ITEM_PAGE)
        if self.page is None:
            self.page = rows.index(s.get('item')) // ITEM_PAGE if s.get('item') in rows else 0
        self.page = min(max(self.page, 0), pages - 1)
        shown = rows[self.page * ITEM_PAGE:(self.page + 1) * ITEM_PAGE]
        labels, types, seen = [], [], set()
        if self.page > 0:
            labels.append(PREV_PAGE)
            types.append(PREV_PAGE)
        for t in shown:
            nm = self.items[t]['name']
            labels.append(nm if nm not in seen else '%s #%d' % (nm, t))
            types.append(t)
            seen.add(nm)
        if self.page < pages - 1:
            labels.append(NEXT_PAGE)
            types.append(NEXT_PAGE)
        if s.get('item') not in shown:      # the chosen item is not in this list: its first item
            s['item'] = shown[0] if shown else None
            self.save()
        cur = labels[types.index(s['item'])] if s['item'] in types else '--'
        win['itemTypes'] = types
        win['item'] = self.dropdown('item', cur, labels or ['--'])
        self.table()

    def table(self):
        '''the Controls-style table for the chosen item (rebuilt when it changes)'''
        n, win = self.n, self.win
        old = win.pop('table', None)
        if old is not None:
            n.delete_child(ffi.cast('void *', win['dlg']), ffi.cast('void *', old))
        t = self.settings.get('item')
        col_w = win['colW']
        tw = NAME_W + len(COLUMNS) * col_w
        rows = matrix_rows(t) if t is not None else []
        tbl = n.container(win['tx'], TOP_Y, tw, ROW_H * (max(1, len(rows)) + 1))
        win['table'], win['cells'], win['heads'], win['hover'] = _addr(tbl), [], [], None
        rules = self.settings['rules'].get(str(t), {})
        shown = COLUMNS[:max_mods(t) + 1] if t is not None else COLUMNS
        for c, text in enumerate(shown):       # only as many columns as it can have mods
            mode = rules.get(str(c), {}).get(ANY, 0)
            tag, color = HEAD_LOOK[mode]
            lb = n.label(tbl, tag + text, 0, 0, color=color)
            e = ffi.cast('struct UIElement *', lb)
            e.x = NAME_W + c * col_w + (col_w - e.w) // 2
            if t is not None and rows:
                win['heads'].append({'el': _addr(lb), 'x': NAME_W + c * col_w, 'y': 0,
                                     'count': c, 'mode': mode, 'text': text})
        if t is None:
            n.label(tbl, 'No item', 0, ROW_H)
        for i, (stat, name, cols) in enumerate(rows):
            y = ROW_H * (i + 1)
            n.label(tbl, name, 0, y)
            for c in cols:
                if c == 0:
                    continue    # Stock is set by its header only (no cells)
                v = rules.get(str(c), {}).get(stat, 0)
                text, color = self.look(c, v)
                lb = n.label(tbl, text, 0, y, color=color, font=CELL_FONT)
                cell = {'el': _addr(lb), 'x': NAME_W + c * col_w, 'y': y, 'count': c, 'stat': stat, 'v': v}
                self.centre(cell)
                win['cells'].append(cell)
        n.add(ffi.cast('void *', win['dlg']), tbl)

    def centre(self, cell):
        e = ffi.cast('struct UIElement *', cell['el'])
        e.x = cell['x'] + (self.win['colW'] - e.w) // 2

    def colMode(self, count):
        '''this column of the chosen item: 0 normal, 1 ANY, -1 NONE'''
        col = self.settings['rules'].get(str(self.settings.get('item')), {}).get(str(count), {})
        return col.get(ANY, 0)

    def look(self, count, v):
        '''(text, color) of a cell: in an ANY column only X shows (the rest is a green
        dash), in a NONE column every cell is an X; the marks are kept for when the
        column is switched back'''
        mode = self.colMode(count)
        if mode == -1:
            return CELL[-1]
        if mode == 1 and v != -1:
            return CELL[0][0], GREEN
        return CELL[v]

    def paint(self, cell):
        text, color = self.look(cell['count'], cell['v'])
        lb = ffi.cast('void *', cell['el'])
        self.n.set_text(lb, self.n.cstr(text))
        self.n.set_color(lb, color)
        self.centre(cell)

    def cycle(self, cell):
        '''-- -> check -> X -> --; saved as rules[item][mod count][stat]. In an ANY column
        a click only puts an X on or takes it off; a NONE column ignores it.'''
        mode = self.colMode(cell['count'])
        if mode == -1:
            return              # NONE: the whole column is X, nothing to change
        if mode == 1:
            v = 0 if cell['v'] == -1 else -1
        else:
            v = {0: 1, 1: -1, -1: 0}[cell['v']]
        self.setCell(cell, v)
        self.save()

    def toggleAny(self, head):
        '''a column header click: normal -> ANY (green: any item, X marks still count) ->
        NONE (red: no item) -> normal. The cells' marks are kept throughout.'''
        self.setMode(head, {0: 1, 1: -1, -1: 0}[head['mode']])

    def setMode(self, head, mode):
        head['mode'] = mode
        tag, color = HEAD_LOOK[mode]
        lb = ffi.cast('void *', head['el'])
        self.n.set_text(lb, self.n.cstr(tag + head['text']))
        self.n.set_color(lb, WHITE if self.win.get('hover') is head else color)
        self.centre(head)
        rules = self.settings['rules']
        item = rules.setdefault(str(self.settings['item']), {})
        col = item.setdefault(str(head['count']), {})
        if head['mode']:
            col[ANY] = head['mode']
        else:
            col.pop(ANY, None)
            if not col:
                item.pop(str(head['count']))
            if not item:
                rules.pop(str(self.settings['item']))
        for cell in self.win['cells']:      # its cells: green dashes / all X / back
            if cell['count'] == head['count']:
                self.paint(cell)
        self.save()

    def setCell(self, cell, v):
        cell['v'] = v
        rules = self.settings['rules']
        item = rules.setdefault(str(self.settings['item']), {})
        col = item.setdefault(str(cell['count']), {})
        if v:
            col[str(cell['stat'])] = v
        else:
            col.pop(str(cell['stat']), None)
            if not col:
                item.pop(str(cell['count']))
            if not item:
                rules.pop(str(self.settings['item']))
        self.paint(cell)

    def pollMouse(self):
        '''the mouse, from the game's SDL2.dll each frame (window pixels): a column header
        under it turns white, as the game's menus do; and, without SBPE's mouse patch (no
        onMouseButton callback, as in a vanilla SBPE), a new left button press is a click'''
        if self.win is None:
            return
        if self.mouse is None:
            import cffi
            kffi = cffi.FFI()
            kffi.cdef('uint32_t SDL_GetMouseState(int *x, int *y);')
            self.mouse = (kffi, kffi.dlopen('SDL2.dll'), kffi.new('int[2]'), [0])
        kffi, sdl, xy, was = self.mouse
        buttons = sdl.SDL_GetMouseState(xy, xy + 1) & 5     # SDL left (1) and right (4)
        if not self.mousePatch:
            for mask, button in ((1, 0), (4, 1)):           # as the game's callback: 0 left, 1 other
                if buttons & mask and not was[0] & mask:
                    self.onMouseButton((xy[0], xy[1], button, 1))
        was[0] = buttons
        self.hover(xy[0], xy[1])

    def under(self, items, x, y):
        '''the table cell / header at window pixel x, y, or None'''
        win = self.win
        mx, my = x * self.refs.scaleX, y * self.refs.scaleY     # window -> UI pixels
        ax, ay = _screen_pos(win['table'])
        for it in items:
            cx, cy = ax + it['x'], ay + it['y'] - 8
            if cx <= mx < cx + win['colW'] and cy <= my < cy + ROW_H:
                return it
        return None

    def hover(self, x, y):
        '''the header under the mouse is white (black outline, as every Label here)'''
        win = self.win
        busy = win.get('set') is not None or win.get('confirm') is not None
        head = None if busy or not self.alive() else self.under(win.get('heads', []), x, y)
        old = win.get('hover')
        if head is old:
            return
        if old is not None and old in win.get('heads', []):
            self.n.set_color(ffi.cast('void *', old['el']), HEAD_LOOK[old['mode']][1])
        if head is not None:
            self.n.set_color(ffi.cast('void *', head['el']), WHITE)
        win['hover'] = head

    def onMouseButton(self, inputs):
        '''a left click on a table cell / header cycles it, a right click puts it back to
        -- / the plain header (the click is kept from the game). The game's button is 0
        for the left button, 1 for any other (XDL_DoEvents)'''
        win = self.win
        if (win is None or not (win.get('cells') or win.get('heads')) or win.get('set') is not None
                or win.get('confirm') is not None):
            return
        x, y, button, down = inputs
        try:
            if not self.alive():
                return
            cell = self.under(win['cells'] + win.get('heads', []), x, y)
            if cell is not None:
                if self.mousePatch:     # keep the click from the game (the patch reads it)
                    self.refs.clickConsumed = True
                if down:
                    right = button != 0
                    if 'stat' in cell:
                        if not right:
                            self.cycle(cell)
                        elif cell['v'] and self.colMode(cell['count']) != -1:
                            self.setCell(cell, 0)
                            self.save()
                    elif not right:
                        self.toggleAny(cell)
                    elif cell['mode']:
                        self.setMode(cell, 0)
        except Exception:
            logging.exception('lootr: table click failed')

    def windowOpen(self):
        '''the Lootr window is on screen (other plugins' drawing is hidden then): it is in
        the Esc menu and it and every parent up to the top are shown (a closed Esc menu
        can stay in the tree, hidden)'''
        if self.win is None or not self.alive():
            return False
        e = ffi.cast('struct UIElement *', self.win['dlg'])
        for _ in range(32):
            if not e.show:
                return False
            if e.parent == ffi.NULL:
                return True
            e = ffi.cast('struct UIElement *', e.parent)
        return True

    def alive(self):
        '''the dialog is still in the Esc menu, and the Esc menu still exists'''
        win = self.win
        gc = self.refs.GameClient
        if gc == ffi.NULL:
            return False
        tops = [_addr(t) for t in self.refs.tops or ()]
        if win['gm'] not in tops and win['gm'] not in _children(gc):
            return False
        return win['dlg'] in _children(win['gm'])

    def poll(self):
        '''read the dropdowns (the game changes them on click); rebuild what depends on them'''
        win, s = self.win, self.settings
        rebuild = False
        for key, names in (('class', CLASS_FILTERS), ('slot', SLOT_FILTERS)):
            row = win[key]
            txt = label_text(row['label'])
            if txt != row['value'] and txt in row['options']:
                row['value'] = txt
                s[key] = names[row['options'].index(txt)][1]
                self.page, rebuild = None, True
        it = win['item']
        txt = label_text(it['label'])
        if not rebuild and txt != it['value'] and txt in it['options']:
            it['value'] = txt
            t = win['itemTypes'][it['options'].index(txt)]
            if t in (PREV_PAGE, NEXT_PAGE):
                self.page += -1 if t == PREV_PAGE else 1
                s['item'] = None        # the new page opens on its first item
                rebuild = True
            elif t != s.get('item'):
                s['item'] = t
                self.save()
                self.table()
        if rebuild:
            self.save()
            self.itemDropdown()

    # Highlight Items / Magnify Items ########################################

    def lootObjects(self):
        '''{(world id, obj id): Loot object} of the loot in the world'''
        cw = self.refs.ClientWorld
        if cw == ffi.NULL:
            return {}
        worlds = [cw.serverSubWorld] + util.sVecMap2list(
            cw.clientSubWorlds, 'struct ForeignSubWorld *')
        if cw.mySubWorld != ffi.NULL:   # a ClientSubWorld: its objects are in its NativeSubWorld
            worlds.append(ffi.addressof(cw.mySubWorld.asNativeSubWorld))
        out = {}
        for sw in worlds:
            if sw == ffi.NULL:
                continue
            wid = int(ffi.cast('struct SubWorld *', sw).worldId)
            for o in util.worldobjects(sw):
                cls = ffi.cast('void **', o)[0]
                if cls != self.lootClass:
                    if self.lootClass is not None or util.getClassName(o) != 'Loot':
                        continue
                    self.lootClass = cls
                out[(wid, int(o.objId))] = o
        return out

    @staticmethod
    def lootItem(o):
        '''(item type, [stat ids]) of a Loot object'''
        ip = ffi.cast('struct Loot *', o).itemProps
        rp = ip.statboosts
        return int(ip.type), [int(ffi.cast('struct StatBoost *', rp.elements[i]).stat)
                              for i in range(max(0, min(rp.current_size, 16)))]

    @staticmethod
    def signature(ip):
        '''(type, ((stat, val), ...)) of an ItemProperties: the same item in the inventory
        and on the ground'''
        rp = ip.statboosts
        boosts = []
        for i in range(max(0, min(rp.current_size, 16))):
            b = ffi.cast('struct StatBoost *', rp.elements[i])
            boosts.append((int(b.stat), int(b.val)))
        return int(ip.type), tuple(sorted(boosts))

    def itemSig(self, item):
        return self.signature(ffi.cast('struct Item *', item).itemProps)

    def lootSig(self, o):
        return self.signature(ffi.cast('struct Loot *', o).itemProps)

    @staticmethod
    def objCentre(o):
        '''an object's centre, world px'''
        q = ffi.cast('struct WorldObject *', o).props
        return (q.xmp + q.wmp // 2) / 256.0, (q.ymp + q.hmp // 2) / 256.0

    def trackDrops(self):
        '''loot that came out of your own inventory: an item leaves your equipped / backpack
        slots and loot with the same type and mods (and values) appears near you within
        DROP_MATCH seconds (either order). Those ObjKeys go in self.mine.'''
        pc = self.pc()
        if pc is None or self.n is None:
            self.ownItems, self.lootKeys = None, None
            return
        now = time.perf_counter()
        have = {}
        for slot in OWN_SLOTS:
            it = self.n.get_item(pc, slot)
            if it != ffi.NULL:
                sig = self.itemSig(it)
                have[sig] = have.get(sig, 0) + 1
        if self.ownItems is not None:
            for sig, n in self.ownItems.items():
                for _ in range(n - have.get(sig, 0)):
                    self.dropped.append((now, sig))
        self.ownItems = have
        loot = self.lootObjects()
        keys = set(loot)
        px, py = self.objCentre(pc)
        if self.lootKeys is not None:
            for key in keys - self.lootKeys:
                qx, qy = self.objCentre(loot[key])
                if abs(qx - px) <= DROP_NEAR and abs(qy - py) <= DROP_NEAR:
                    self.newLoot.append((now, key, self.lootSig(loot[key])))
        self.lootKeys = keys
        self.dropped = [d for d in self.dropped if now - d[0] <= DROP_MATCH]
        self.newLoot = [d for d in self.newLoot if now - d[0] <= DROP_MATCH and d[1] in keys]
        for d in list(self.dropped):
            for nl in self.newLoot:
                if nl[2] == d[1]:
                    self.mine.add(nl[1])
                    self.newLoot.remove(nl)
                    self.dropped.remove(d)
                    break
        self.mine &= keys       # forget picked up / gone ones

    def itemName(self, t, stats):
        '''as the game names it, e.g. "Experimental Blasphemous Antiphon"'''
        rec = ITEMS.get(t) or UNUSED_ITEMS.get(t) or {}
        name = rec.get('name') or 'item %d' % t
        rank = rank_of(stats)
        return '%s %s' % (RANKS[rank], name) if rank else name

    def wantedLoot(self):
        '''[(x, y, w, h, vids, obj, mine)] in world px of the loot on the ground the table
        wants; mine: you dropped it'''
        rules, out = self.settings['rules'], []
        for key, o in self.lootObjects().items():
            t, stats = self.lootItem(o)
            if not wants(rules, t, stats):
                continue
            p = o.props
            vids = [util.getstr(p.vid)]
            desc = ffi.cast('struct Loot *', o).itemDesc
            if desc != ffi.NULL and desc.lootvid != ffi.NULL:
                vids.append(util.getstr(desc.lootvid))
            out.append((p.xmp / 256.0, p.ymp / 256.0, p.wmp / 256.0, p.hmp / 256.0,
                        [v for v in vids if v and v != '(NULL)'], o, key in self.mine))
        return out

    def box(self, x, y, w, h, line=HIGHLIGHT_LINE, back=HIGHLIGHT_FILL):
        '''the highlight: a faint fill and an outline'''
        fill, blend, lw = self.refs.XDL_FillRect, lib.BLENDMODE_BLEND, HIGHLIGHT_W
        fill(x, y, w, h, back, blend)
        fill(x, y, w, lw, line, blend)
        fill(x, y + h - lw, w, lw, line, blend)
        fill(x, y + lw, lw, h - 2 * lw, line, blend)
        fill(x + w - lw, y + lw, lw, h - 2 * lw, line, blend)

    def wantedSlots(self):
        '''[(x, y, w, h)] on screen of the inventory / stash / HUD slots whose item the
        table wants, while the inventory (InventoryOverlay) is open. Its InventoryWindow and
        StashWindow, and the HUD's HUDEquip, hold SlotSprites (slotPos);
        PlayerCharacter::getItem(slotPos) gives the Item there (type, statboosts).'''
        wc, pc = self.refs.WorldClient, self.pc()
        if wc == ffi.NULL or pc is None or wc.overlay == ffi.NULL:
            return []
        ov = wc.overlay
        cls = ffi.cast('void **', ov)[0]
        if cls != self.invClass:
            if self.invClass is not None or util.getClassName(ov) != 'InventoryOverlay':
                return []
            self.invClass = cls
        ov = ffi.cast('struct InventoryOverlay *', ov)
        rules, out = self.settings['rules'], []
        wins = [ov.inventoryWindow, ov.stashWindow]
        if ov.hud != ffi.NULL and ov.hud.hudEquip != ffi.NULL:
            wins.append(ov.hud.hudEquip)    # the HUD's equipped items (HUDEquip.slots)
        for win in wins:
            if win == ffi.NULL or not ffi.cast('struct UIElement *', win).show:
                continue
            for slot in util.vec2list(win.slots, 'struct SlotSprite *'):
                e = ffi.cast('struct UIElement *', slot)
                if not e.show:
                    continue
                item = self.n.get_item(pc, slot.slotPos)
                if item == ffi.NULL:
                    continue
                ip = ffi.cast('struct Item *', item).itemProps
                rp = ip.statboosts
                stats = [ffi.cast('struct StatBoost *', rp.elements[i]).stat
                         for i in range(max(0, min(rp.current_size, 16)))]
                if wants(rules, ip.type, stats):
                    x, y = _screen_pos(slot)
                    out.append((x, y, e.w, e.h))
        return out

    def onPresent(self):
        s = self.settings
        if self.gate is not None and self.gate.get('owner') == id(self) and self.windowOpen():
            return              # nothing over the Lootr window (its own drawing included)
        try:
            self.drawMessages()
        except Exception:
            logging.exception('lootr: message drawing failed')
            self.messages = []
        if self.n is None or self.drawFailed:
            return
        if s.get('highlight_inv'):
            try:
                for x, y, w, h in self.wantedSlots():
                    self.box(x, y, max(1, w), max(1, h))
            except Exception:
                logging.exception('lootr: reading the inventory failed, Highlight Items In Inventory is off')
                self.drawFailed = True
                return
        if s.get('chest_contents') and not self.chestFailed:
            try:
                self.drawChests()
            except Exception:
                logging.exception('lootr: chest drawing failed, Show Chest Contents is off until reload')
                self.chestFailed = True
        if not (s.get('highlight') or s.get('magnify')):
            return
        wv = self.refs.WorldView
        if wv == ffi.NULL:
            return
        try:
            loot = self.wantedLoot()
        except Exception:
            # stop drawing until the plugin reloads (logged once); the settings stay as set
            logging.exception('lootr: reading loot failed, Highlight / Magnify Items are off')
            self.drawFailed = True
            return
        ox, oy = wv.offset.x, wv.offset.y
        for wx, wy, ww, wh, vid, obj, mine in loot:
            x, y, w, h = int(wx - ox), int(wy - oy), max(1, int(ww)), max(1, int(wh))
            if mine:            # you dropped it: yellow, and not magnified (not to be picked up)
                if s.get('highlight'):
                    self.box(x, y, w, h, MINE_LINE, MINE_FILL)
                continue
            if s.get('highlight'):
                self.box(x, y, w, h)
            if s.get('magnify'):
                self.magnify(wv, obj, wx, wy, ww, wh, vid)

    # Show Chest Contents ####################################################

    def chestObjects(self):
        '''the Chest objects in the world'''
        cw = self.refs.ClientWorld
        if cw == ffi.NULL:
            return []
        worlds = [cw.serverSubWorld] + util.sVecMap2list(
            cw.clientSubWorlds, 'struct ForeignSubWorld *')
        if cw.mySubWorld != ffi.NULL:
            worlds.append(ffi.addressof(cw.mySubWorld.asNativeSubWorld))
        out, seen = [], set()
        for sw in worlds:
            if sw == ffi.NULL:
                continue
            for o in util.worldobjects(sw):
                cls = ffi.cast('void **', o)[0]
                if cls != self.chestClass:
                    if self.chestClass is not None or util.getClassName(o) != 'Chest':
                        continue
                    self.chestClass = cls
                a = _addr(o)
                if a not in seen:
                    seen.add(a)
                    out.append(o)
        return out

    @staticmethod
    def chestItems(o):
        '''[(type, [(stat, val)], ItemProperties *)] of the items still in a chest
        (index >= Chest.pos)'''
        c = ffi.cast('char *', o)
        pos = ffi.cast('int32_t *', c + CHEST_POS)[0]
        n = max(0, min(ffi.cast('int32_t *', c + CHEST_COUNT)[0], 64))
        elements = ffi.cast('void ***', c + CHEST_COUNT - 4)[0]
        out = []
        for i in range(max(pos, 0), n):
            ip = ffi.cast('struct ItemProperties *', elements[i])
            if ip == ffi.NULL:
                continue
            rp = ip.statboosts
            boosts = []
            for j in range(max(0, min(rp.current_size, 16))):
                b = ffi.cast('struct StatBoost *', rp.elements[j])
                boosts.append((int(b.stat), int(b.val)))
            out.append((int(ip.type), boosts, ip))
        return out

    @staticmethod
    def gives(t, boosts, stat):
        '''how much of a stat a pickup gives (its boosts, else its known base), 0 = none'''
        n = sum(v for st, v in boosts if st == stat)
        if n:
            return n
        rec = UNUSED_ITEMS.get(t) or {}
        return sum(v for st, v in rec.get('base', []) if st == stat)

    def needHp(self):
        '''below full HP (as extra_info's HP arrows)'''
        pc = self.pc()
        if pc is None:
            return False
        p = ffi.cast('struct WorldObject *', pc).props
        return p.hitpoints < p.maxhitpoints

    def chestShow(self, o, rules, needHp):
        '''[(type, ItemProperties *, vid)] to draw above a chest: the items still in it the
        table wants, and its HP pickups when you are hurt'''
        out = []
        for t, b, ip in self.chestItems(o):
            if self.gives(t, b, HP_STAT):
                ok = needHp
            else:
                ok = wants(rules, t, [st for st, _v in b])
            if ok:
                vid = self.n.lootvid(t)
                if vid:
                    out.append((t, ip, vid))
        return out[:CHEST_MAX]

    def chestLootFor(self, chest, t, ip):
        '''the Loot that draws item type t for this chest (built once per sub-world)'''
        sw = ffi.cast('void **', ffi.cast('char *', chest) + CHEST_SUBWORLD)[0]
        key = (_addr(sw), t)
        if key not in self.chestLoot:
            self.chestLoot[key] = self.n.make_loot(sw, ip)
        return self.chestLoot[key]

    def drawChests(self):
        wv = self.refs.WorldView
        if wv == ffi.NULL or self.refs.ClientWorld == ffi.NULL:
            return
        if self.chestOk is None:
            # Chest fields are read at the offsets Chest::throwLoot / internalUpdate use
            self.chestOk = ffi.offsetof('struct WorldView', 'offset') == 0x90
            if not self.chestOk:
                logging.error('lootr: WorldView layout differs (game updated?), '
                              'Show Chest Contents is off')
        if not self.chestOk:
            return
        chests = self.chestObjects()
        if not chests:
            self.chestLoot = {}
            return
        # Loots built for a sub-world no chest is in any more point at a gone sub-world
        live = {_addr(ffi.cast('void **', ffi.cast('char *', o) + CHEST_SUBWORLD)[0])
                for o in chests}
        for key in [k for k in self.chestLoot if k[0] not in live]:
            del self.chestLoot[key]
        rules, hurt = self.settings['rules'], self.needHp()
        for o in chests:
            shown = self.chestShow(o, rules, hurt)
            row = []                # (Loot drawn, sprite w, sprite h)
            for t, ip, vid in shown:
                sprite = self.n.image(vid)      # its size, as magnify() takes it
                if sprite is not None:
                    row.append((self.chestLootFor(o, t, ip), sprite['w'], sprite['h']))
            if row:
                self.drawRow(wv, o, row)

    def chestTop(self, chest):
        '''world y of the top of the chest as drawn: its sprite is drawn up from its
        bottom centre (or around its centre), and can be taller than its box'''
        p = chest.props
        top = p.ymp / 256.0
        sprite = self.n.image(util.getstr(p.vid))
        if sprite is not None:
            if ffi.cast('uint8_t *', chest)[OBJ_CENTRED]:
                top = min(top, (p.ymp + p.hmp / 2.0) / 256.0 - sprite['h'] / 2.0)
            else:
                top = min(top, (p.ymp + p.hmp) / 256.0 - sprite['h'])
        return top

    def drawRow(self, wv, chest, row):
        '''the sprites MAGNIFY times larger in a row centred above the chest, their bottoms
        above its top'''
        k = MAGNIFY
        p = chest.props
        total = sum(w * k for _o, w, _h in row) + CHEST_GAP * (len(row) - 1)
        x = (p.xmp + p.wmp / 2.0) / 256.0 - wv.offset.x - total / 2.0
        bottom = self.chestTop(chest) - wv.offset.y - MAGNIFY_GAP - CHEST_LIFT
        for obj, w, h in row:
            # its centre: the middle of its slot, half its (enlarged) height above bottom
            self.drawAbove(wv, obj, x + w * k / 2.0, bottom - h * k / 2.0)
            x += w * k + CHEST_GAP

    def drawAbove(self, wv, obj, tx, ty):
        '''draw a Loot's sprite MAGNIFY times larger centred on (tx, ty) (screen px at
        normal size) exactly as magnify() draws loot on the ground: the object's centre is
        put there with a canvas MAGNIFY times smaller and the view offset moved, then the
        game's own WorldView::drawObjectVisual(loot)'''
        k = MAGNIFY
        if ffi.typeof(obj) == ffi.typeof('void *'):
            obj = ffi.cast('struct WorldObject *', obj)
        p = obj.props
        cx, cy = (p.xmp + p.wmp / 2.0) / 256.0, (p.ymp + p.hmp / 2.0) / 256.0   # its centre
        ox, oy = wv.offset.x, wv.offset.y
        cw0, ch0 = self.refs.canvasW_[0], self.refs.canvasH_[0]
        try:
            self.refs.canvasW_[0] = int(round(cw0 / float(k)))
            self.refs.canvasH_[0] = int(round(ch0 / float(k)))
            wv.offset.x = int(round(cx - tx / k))
            wv.offset.y = int(round(cy - ty / k))
            self.n.draw_obj_visual(wv, obj)
        finally:
            self.refs.canvasW_[0], self.refs.canvasH_[0] = cw0, ch0
            wv.offset.x, wv.offset.y = ox, oy

    def magnify(self, wv, obj, wx, wy, ww, wh, vids):
        '''draw the loot exactly as the game does (WorldView::drawObjectVisual: its own
        animation, layers and image swaps), MAGNIFY times larger, above the item. XDL scales
        drawing by window / canvas size, so a canvas MAGNIFY times smaller draws MAGNIFY
        times larger; the view offset is moved so the copy lands above the item. Both are
        put back right after.'''
        if self.offsetOk is None:   # drawImage reads WorldView offset at +0x90
            self.offsetOk = ffi.offsetof('struct WorldView', 'offset') == 0x90
            if not self.offsetOk:
                logging.error('lootr: WorldView layout differs (game updated?), Magnify Items is off')
        if not self.offsetOk:
            return
        k = MAGNIFY
        sh = wh
        for v in vids:              # the sprite's height, for where the copy goes
            sprite = self.n.image(v)
            if sprite is not None:
                sh = sprite['h']
                break
        ox, oy = wv.offset.x, wv.offset.y
        cx, cy = wx + ww / 2.0, wy + wh / 2.0          # the item's centre (world px)
        # where its centre should be drawn (screen px at normal size): above the item
        tx = cx - ox
        ty = (wy - oy) - MAGNIFY_GAP - sh * k / 2.0
        cw0, ch0 = self.refs.canvasW_[0], self.refs.canvasH_[0]
        try:
            self.refs.canvasW_[0] = int(round(cw0 / float(k)))
            self.refs.canvasH_[0] = int(round(ch0 / float(k)))
            wv.offset.x = int(round(cx - tx / k))
            wv.offset.y = int(round(cy - ty / k))
            self.n.draw_obj_visual(wv, obj)
        finally:
            self.refs.canvasW_[0], self.refs.canvasH_[0] = cw0, ch0
            wv.offset.x, wv.offset.y = ox, oy

    def __del__(self):
        gate = getattr(self, 'gate', None)
        if gate is not None and gate.get('owner') == id(self):
            gate['open'] = None     # plugin removed/disabled: nothing is hidden any more
        st = getattr(self, 'st', None)
        if st is not None and st.get('owner') == id(self):
            st['enabled'] = False   # plugin removed/disabled: the button goes away
            st['open'] = None
