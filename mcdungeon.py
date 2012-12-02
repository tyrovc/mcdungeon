#!/usr/bin/python

import sys
import os
import argparse
import logging
import re
import time
import cPickle
from numpy import *

# Silence some logging from pymclevel
logging.basicConfig(level=logging.CRITICAL)

from pymclevel import mclevel
from overviewer_core import world as ov_world
import pmeter

# Version info
__version__ = '0.10.4'
__version_info__ = tuple([ num for num in __version__.split('.')])
_vstring = '%%(prog)s %s' % (__version__)

# Argument parsers
parser = argparse.ArgumentParser(
    description='Generate a tile-based dungeon in a Minecraft map.')
parser.add_argument('-v', '--version',
                           action='version', version=_vstring,
                           help='Print version and exit')
subparsers = parser.add_subparsers(
                                   description='See "COMMAND --help" for \
                                   additional help.',
                                   title='Available commands')

# Interactive subcommand parser
parser_inter= subparsers.add_parser('interactive',
                                    help='Interactive mode.')
parser_inter.set_defaults(command='interactive')
parser_inter.add_argument('--skip-relight',
                    action='store_true',
                    dest='skiprelight',
                    help='Skip relighting the level')
parser_inter.add_argument('-t','--term',
                    type=int,dest='term',
                    metavar='FLOOR',
                    help='Print a text version of a given floor to the \
                    terminal')
parser_inter.add_argument('--html',
                    dest='html',
                    metavar='BASENAME',
                    help='Output html versions of the dungeon. This \
                    produces one file per level of the form \
                    BASENAME-(level number).html')
parser_inter.add_argument('--debug',
                    action='store_true',
                    dest='debug',
                    help='Provide additional debug info')
parser_inter.add_argument('--force',
                    action='store_true',
                    dest='force',
                    help='Force overwriting of html output files')
parser_inter.add_argument('-s', '--seed',
                    dest='seed',
                    metavar='SEED',
                    help='Provide a seed for this dungeon. This can be \
                    anything')
parser_inter.add_argument('-o', '--offset',
                    dest='offset',
                    nargs=3,
                    type=int,
                    metavar=('X', 'Y', 'Z'),
                    help='Provide a location offset in blocks')
parser_inter.add_argument('--force-bury',
                    action='store_true',
                    dest='bury',
                    help='Attempt to calculate Y when using --offset')
parser_inter.add_argument('-e', '--entrance',
                    dest='entrance',
                    nargs=2,
                    type=int,
                    metavar=('X', 'Z'),
                    help='Provide an offset for the entrance in chunks')
parser_inter.add_argument('--spawn',
                    dest='spawn',
                    nargs=2,
                    type=int,
                    metavar=('X', 'Z'),
                    help='Override spawn point')
parser_inter.add_argument('--dir',
                          dest='dir',
                          metavar='SAVEDIR',
                          help='Override the default map directory.')
parser_inter.add_argument('--mapstore',
                    dest='mapstore',
                    metavar='PATH',
                    help='Provide an alternate world to store maps.')

# Add subcommand parser 
parser_add = subparsers.add_parser('add', help='Add new dungeons.')
parser_add.set_defaults(command='add')
parser_add.add_argument('world',
                    metavar='SAVEDIR',
                    help='Target world (path to save directory)')
parser_add.add_argument('x',
                    metavar='X',
                    help='Number of rooms West -> East, or provide a range.')
parser_add.add_argument('z',
                    metavar='Z',
                    help='Number of rooms North -> South, or provide a range. (ie: 4-7)')
parser_add.add_argument('levels',
                    metavar='LEVELS',
                    help='Number of levels. Enter a positive value, or \
                        provide a range.')
parser_add.add_argument('-c', '--config',
                    dest='config',
                    metavar='CFGFILE',
                    default='default.cfg',
                    help='Alternate config file. Default: default.cfg')
parser_add.add_argument('--write',
                    action='store_true',
                    dest='write' ,
                    help='Write the dungeon to disk')
parser_add.add_argument('--skip-relight',
                    action='store_true',
                    dest='skiprelight',
                    help='Skip relighting the level')
parser_add.add_argument('-t','--term',
                    type=int,dest='term',
                    metavar='FLOOR',
                    help='Print a text version of a given floor to the \
                    terminal')
parser_add.add_argument('--html',
                    dest='html',
                    metavar='BASENAME',
                    help='Output html versions of the dungeon. This \
                    produces one file per level of the form \
                    BASENAME-(level number).html')
parser_add.add_argument('--debug',
                    action='store_true',
                    dest='debug',
                    help='Provide additional debug info')
parser_add.add_argument('--force',
                    action='store_true',
                    dest='force',
                    help='Force overwriting of html output files')
parser_add.add_argument('-s', '--seed',
                    dest='seed',
                    metavar='SEED',
                    help='Provide a seed for this dungeon. This can be \
                    anything')
parser_add.add_argument('-o', '--offset',
                    dest='offset',
                    nargs=3,
                    type=int,
                    metavar=('X', 'Y', 'Z'),
                    help='Provide a location offset in blocks')
parser_add.add_argument('--force-bury',
                    action='store_true',
                    dest='bury',
                    help='Attempt to calculate Y when using --offset')
parser_add.add_argument('-e', '--entrance',
                    dest='entrance',
                    nargs=2,
                    type=int,
                    metavar=('X', 'Z'),
                    help='Provide an offset for the entrance in chunks')
parser_add.add_argument('--spawn',
                    dest='spawn',
                    nargs=2,
                    type=int,
                    metavar=('X', 'Z'),
                    help='Override spawn point')
parser_add.add_argument('-n','--number',
                    type=int,dest='number',
                    metavar='NUM',
                    default=1,
                    help='Number of dungeons to generate. -1 will create as \
                    many as possible given X, Z, and LEVEL settings.')
parser_add.add_argument('--mapstore',
                    dest='mapstore',
                    metavar='PATH',
                    help='Provide an alternate world to store maps.')

# List subcommand parser
parser_list= subparsers.add_parser('list',
                                    help='List known dungeons in a map.')
parser_list.set_defaults(command='list')
parser_list.add_argument('world',
                    metavar='SAVEDIR',
                    help='Target world (path to save directory)')

# Delete subcommand parser
parser_del= subparsers.add_parser('delete',
                                    help='Delete dungeons from a map.')
parser_del.set_defaults(command='delete')
parser_del.add_argument('world',
                    metavar='SAVEDIR',
                    help='Target world (path to save directory)')
parser_del.add_argument('-d', '--dungeon',
                    metavar=('X', 'Z'),
                    nargs=2,
                    action='append',
                    dest='dungeons',
                    type=int,
                    help='The X Z coordinates of a dungeon to delete. \
                        NOTE: These will be rounded to the nearest chunk. \
                        Multiple -d flags can be specified.')
parser_del.add_argument('-a', '--all',
                    dest='all',
                    action='store_true',
                    help='Delete all known dungeons. Overrides -d.')
parser_del.add_argument('--mapstore',
                    dest='mapstore',
                    metavar='PATH',
                    help='Provide an alternate world to store maps.')

# Regnerate subcommand parser
parser_regen= subparsers.add_parser('regenerate',
                                    help='Regenerate dungeons in a map.')
parser_regen.set_defaults(command='regenerate')
parser_regen.add_argument('world',
                    metavar='SAVEDIR',
                    help='Target world (path to save directory)')
parser_regen.add_argument('-d', '--dungeon',
                    metavar=('X', 'Z'),
                    nargs=2,
                    required=True,
                    dest='dungeon',
                    type=int,
                    help='The X Z coordinates of a dungeon to regenerate. \
                        NOTE: These will be rounded to the nearest chunk. \
                        Only one dungeon at a time can be specified.')
parser_regen.add_argument('-c', '--config',
                    dest='config',
                    metavar='CFGFILE',
                    default='default.cfg',
                    help='Alternate config file. Default: default.cfg')
parser_regen.add_argument('--debug',
                    action='store_true',
                    dest='debug',
                    help='Provide additional debug info')
parser_regen.add_argument('--html',
                    dest='html',
                    metavar='BASENAME',
                    help='Output html versions of the dungeon. This \
                    produces one file per level of the form \
                    BASENAME-(level number).html')
parser_regen.add_argument('--force',
                    action='store_true',
                    dest='force',
                    help='Force overwriting of html output files')
parser_regen.add_argument('-t','--term',
                    type=int,dest='term',
                    metavar='FLOOR',
                    help='Print a text version of a given floor to the \
                    terminal')
parser_regen.add_argument('--skip-relight',
                    action='store_true',
                    dest='skiprelight',
                    help='Skip relighting the level')
parser_regen.add_argument('--mapstore',
                    dest='mapstore',
                    metavar='PATH',
                    help='Provide an alternate world to store maps.')
#parser_regen.add_argument('-a', '--all',
#                    dest='all',
#                    action='store_true',
#                    help='Regenerate all known dungeons. Overrides -d.')


# Parse the args
args = parser.parse_args()

import cfg
import loottable
from dungeon import *
from utils import *
import mapstore

def loadWorld(world_name):
    '''Attempt to load a world file. Look in the literal path first, then look
    in the typical save directory for the given platform. Check to see if the
    mcdungeon cache directory exists, and create it if not.'''
    # Attempt to open the world. Look in cwd first, then try to search the
    # user's save directory. 
    global cfg
    global cache_path

    world = None
    try:
        print "Trying to open:", world_name
        world = mclevel.fromFile(world_name)
        oworld = ov_world.World(world_name)
    except:
        saveFileDir = mclevel.saveFileDir
        world_name = os.path.join(saveFileDir, world_name)
        print "Trying to open:", world_name
        try:
            world = mclevel.fromFile(world_name)
            oworld = ov_world.World(world_name)
        except:
            print "Failed to open world:",world_name
            sys.exit(1)
    print 'Loaded world: %s (%d chunks, %d blocks high)' % (world_name,
                                                            world.chunkCount,
                                                            world.Height)
    # Create the mcdungeon cahce dir if needed. 
    cache_path = os.path.join(world_name, cfg.cache_dir)
    if os.path.exists(cache_path) is False:
        os.makedirs(cache_path)

    # Find the mapstore path
    print 'Looking for data directory:', os.path.join(cfg.mapstore, 'data')
    if not os.path.exists(os.path.join(cfg.mapstore, 'data')):
        cfg.mapstore = os.path.join(mclevel.saveFileDir, cfg.mapstore)
        print 'Looking for data directory:', os.path.join(cfg.mapstore, 'data')
        if not os.path.exists(os.path.join(cfg.mapstore, 'data')):
            print "Cannot find world data directory!"
            sys.exit(1)

    return world, oworld

def listDungeons(world, oworld, expand_hard_mode=False):
    '''Scan a world for dungeons. Try to cache the results and only look at
    chunks that have changed since the last run.'''
    global cache_path
    pm = pmeter.ProgressMeter()

    # Try to load the cache
    dungeonCacheOld, mtime = loadDungeonCache(cache_path)
    dungeonCache = {}

    # Scan with overviewer
    regions = oworld.get_regionset("overworld")
    count = world.chunkCount
    cached = 0
    notcached = 0
    print 'Scanning world for existing dungeons:'
    print 'cache mtime: %d' % (mtime)
    pm.init(count, label='')
    for cx, cz, cmtime in regions.iterate_chunks():
        count -= 1
        pm.update_left(count)
        key = '%s,%s' % (cx*16, cz*16)
        if cmtime < mtime and key not in dungeonCacheOld:
            cached += 1
            continue
        notcached += 1
        for tileEntity in regions.get_chunk(cx, cz)["TileEntities"]:
            if tileEntity['id'] == 'Sign' and tileEntity['Text1'].startswith('[MCD]'):
                key = '%s,%s' % (tileEntity["x"], tileEntity["z"])
                dungeonCache[key] = tileEntity
    pm.set_complete()
    print ' Cache hit rate: %d/%d (%d%%)' % (cached, world.chunkCount,
                                             100*cached/world.chunkCount)

    saveDungeonCache(cache_path, dungeonCache)

    # Process the dungeons
    dungeons = []
    output = ''
    output += "Known dungeons on this map:\n"
    output += '+-----------+----------------+---------+---------+--------+-------------------+\n'
    output += '| %9s | %14s | %7s | %7s | %6s | %17s |\n' % (
        'Position',
        'Date/Time',
        'Version',
        'Size',
        'Levels',
        'Options'
    )
    output += '+-----------+----------------+---------+---------+--------+-------------------+\n'
    for tileEntity in dungeonCache.values():
        ver = tileEntity["Text1"][5:]
        (major, minor, patch) = ver.split('.')
        version = float(major+'.'+minor)
        (xsize, zsize, levels) = tileEntity["Text3"].split(',')
        offset = 0
        if (expand_hard_mode == True and
            tileEntity["Text4"].find('H:1') >= 0):
            offset = 5
        dungeons.append((int(tileEntity["x"])-offset,
                         int(tileEntity["z"])-offset,
                         int(xsize)+offset,
                         int(zsize)+offset,
                         tileEntity["Text4"],
                         int(levels),
                         int(tileEntity["x"]),
                         int(tileEntity["y"]),
                         int(tileEntity["z"]),
                         version))
        output += '| %9s | %14s | %7s | %7s | %6d | %17s |\n' % (
         '%s %s'%(int(tileEntity["x"]),int(tileEntity["z"])),
            time.strftime('%x %H:%M',
                       time.localtime(int(tileEntity["Text2"]))),
         ver,
         '%sx%s'%(xsize, zsize),
         int(levels),
         tileEntity["Text4"]
        )
    output += '+-----------+--------------------------+---------+--------+-------------------+\n'
    if len(dungeons) > 0:
        print output
    else:
        print 'No dungeons found!'
    return dungeons

# Globals
world = None
oworld = None
cache_path = None
dungeons = []
dungeon_positions = {}
total_rooms = 0
chunk_cache = {}
good_chunks = {}

# Interactive mode
if (args.command == 'interactive'):
    print 'Starting interactive mode!'

    # Pick a map
    saveFileDir = mclevel.saveFileDir
    if args.dir is not None:
        saveFileDir = args.dir
    print '\nYour save directory is:\n', saveFileDir
    if (os.path.isdir(saveFileDir) == False):
        sys.exit('\nI cannot find your save directory! Aborting!')
    print '\nWorlds in your save directory:\n'
    count = 0
    for file in os.listdir(saveFileDir):
        file_path = os.path.join(saveFileDir, file)
        if (os.path.isdir(file_path) and
            os.path.isfile(file_path+'/level.dat')):
            print '   ',file
            count += 1
    if count == 0:
        sys.exit('There do not appear to be any worlds in your save direcory. Aborting!')
    w = raw_input('\nEnter the name of the world you wish to modify: ')
    args.world = os.path.join(saveFileDir, w)

    # Pick a mode
    print '\nChoose an action:\n-----------------\n'
    print '\t[a] Add new dungeon(s) to this map.'
    print '\t[l] List dungeons already in this map.'
    print '\t[d] Delete dungeons from this map.'
    print '\t[r] Regenerate a dungeon in this map.'
    command = raw_input('\nEnter choice or q to quit: ')

    if command == 'a':
        args.command = 'add'
        # Pick a config
        configDir = os.path.join(sys.path[0], 'configs')
        if (os.path.isdir(configDir) == False):
            configDir = 'configs'
        if (os.path.isdir(configDir) == False):
            sys.exit('\nI cannot find your configs directory! Aborting!')
        print '\nConfigurations in your configs directory:\n'
        for file in os.listdir(configDir):
            file_path = os.path.join(configDir, file)
            file = file.replace('.cfg', '')
            if (os.path.isfile(file_path) and
               file_path.endswith('.cfg')):
                print '   ',file
        print '\nEnter the name of the configuration you wish to use.'
        config = raw_input('(leave blank for default): ')
        if (config == ''):
            config = 'default'
        #args.config = str(os.path.join(configDir, config))+'.cfg'
        args.config = str(config)+'.cfg'
        cfg.Load(args.config)

        # Prompt for a mapstore if we need to
        if (cfg.maps > 0 and cfg.mapstore == '' and args.mapstore == None):
            print '\nThis configuration may generate dungeon maps. If you are'
            print 'using bukkit/multiverse you need supply the name of your'
            print 'primary world for this to work. You can also provide this'
            print 'in the config file or as a command switch.'
            print '\n(if you don\'t use bukkit, just hit enter)'
            cfg.mapstore = raw_input('Name of primary bukkit world: ')

        m = cfg.max_dist - cfg.min_dist
        print '\nEnter the size of the dungeon(s) in chunks from West to East. (X size)'
        print 'You can enter a fixed value >= 4, or a range (ie: 4-7)'
        args.x = raw_input('X size: ')

        print '\nEnter the size of the dungeon(s) in chunks from North to South. (Z size)'
        print 'You can enter a fixed value >= 4, or a range (ie: 4-7)'
        args.z = raw_input('Z size: ')

        print '\nEnter a number of levels.'
        print 'You can enter a fixed value >= 1, or a range (ie: 3-5)'
        print 'Enter -1 to pick random values between 1 and 8.'
        args.levels = raw_input('Levels: ')

        print '\nEnter the maximum number of dungeons to add.'
        print 'Depending on the characteristics of your world, and size of your'
        print 'dungeons, the actual number placed may be less.'
        print 'Enter -1 to add as many dungeons as possible.'
        args.number = raw_input('Number of dungeons (leave blank for 1): ')
        if (args.number == ''):
            args.number = 1
        try:
            args.number  = int(args.number)
        except ValueError:
            sys.exit('You must enter an integer.')

        #html = raw_input('\nWould you like to create an HTML map? (y/n): ')
        #if (html.lower() == 'y'):
        #    args.html = world
        #    args.force = True
        args.write = True
    elif command == 'r':
        args.command = 'regenerate'
        # Pick a config
        configDir = os.path.join(sys.path[0], 'configs')
        if (os.path.isdir(configDir) == False):
            configDir = 'configs'
        if (os.path.isdir(configDir) == False):
            sys.exit('\nI cannot find your configs directory! Aborting!')
        print '\nConfigurations in your configs directory:\n'
        for file in os.listdir(configDir):
            file_path = os.path.join(configDir, file)
            file = file.replace('.cfg', '')
            if (os.path.isfile(file_path) and
               file_path.endswith('.cfg')):
                print '   ',file
        print '\nEnter the name of the configuration you wish to use.'
        config = raw_input('(leave blank for default): ')
        if (config == ''):
            config = 'default'
        args.config = str(config)+'.cfg'
        cfg.Load(args.config)

        # Prompt for a mapstore if we need to
        if (cfg.maps > 0 and cfg.mapstore == '' and args.mapstore == None):
            print '\nThis configuration may generate dungeon maps. If you are'
            print 'using bukkit/multiverse you need supply the name of your'
            print 'primary world for this to work. You can also provide this'
            print 'in the config file or as a command switch.'
            print '\n(if you don\'t use bukkit, just hit enter)'
            cfg.mapstore = raw_input('Name of primary bukkit world: ')

        if (cfg.mapstore == ''):
            cfg.mapstore = args.world

        args.dungeon = None
        world, oworld = loadWorld(args.world)
        dlist = listDungeons(world, oworld)
        if len(dlist) == 0:
            sys.exit()
        print 'Choose a dungeon to regenerate:\n-------------------------------\n'
        for i in xrange(len(dlist)):
            print '\t[%d] Dungeon at %d %d.'%(i+1,
                                              dlist[i][0],
                                              dlist[i][1])
        while (args.dungeon == None):
            d = raw_input('\nEnter choice, or q to quit: ')
            if d.isdigit() and int(d) > 0 and int(d) <= len(dlist):
                d = int(d)
                args.dungeon = [dlist[d-1][0], dlist[d-1][1]]
            elif d == 'q':
                print 'Quitting...'
                sys.exit()
            else:
                print '"%s" is not a valid choice!'%d

    elif command == 'l':
        args.command = 'list'
    elif command == 'd':
        args.command = 'delete'
        args.dungeons = []
        args.all = False

        # Prompt for a mapstore if we need to
        if args.mapstore == None:
            print '\nIf you are using bukkit/multiverse you need supply the'
            print 'name of your primary world so any existing dungeon maps'
            print 'can be removed. You can also provide this as a command switch.'
            print '\n(if you don\'t use bukkit, just hit enter)'
            cfg.mapstore = raw_input('Name of primary bukkit world: ')

        if (cfg.mapstore == ''):
            cfg.mapstore = args.world

        world, oworld = loadWorld(args.world)
        dungeons = listDungeons(world, oworld)

        if len(dungeons) == 0:
            sys.exit()
        print 'Choose dungeon(s) to delete:\n----------------------------\n'
        print '\t[a] Delete ALL dungeons from this map.'
        for i in xrange(len(dungeons)):
            print '\t[%d] Dungeon at %d %d.'%(i+1,
                                              dungeons[i][0],
                                              dungeons[i][1])
        while (args.all == False and args.dungeons == []):
            d = raw_input('\nEnter choice, or q to quit: ')
            if d == 'a':
                args.all = True
            elif d.isdigit() and int(d) > 0 and int(d) <= len(dungeons):
                d = int(d)
                args.dungeons = [[dungeons[d-1][0], dungeons[d-1][1]]]
            elif d == 'q':
                print 'Quitting...'
                sys.exit()
            else:
                print '"%s" is not a valid choice!'%d
    else:
        print 'Quitting...'
        sys.exit()
elif(args.command == 'add' or args.command == 'regenerate'):
    cfg.Load(args.config)

# Check to see if mapstore is being overridden
if (hasattr(args, 'mapstore') and args.mapstore is not None):
    cfg.mapstore = args.mapstore
if (cfg.mapstore == ''):
    cfg.mapstore = args.world

# Load the world if we havent already
if world == None:
    world, oworld = loadWorld(args.world)

# List mode
if (args.command == 'list'):
    # List the known dungeons and exit
    dungeons = listDungeons(world, oworld)
    #print dungeons
    sys.exit()

# Delete mode
if (args.command == 'delete'):
    # Check to make sure the user specified what they want to do.
    if args.dungeons == [] and args.all == False:
        print 'You must specify either --all or at least one -d option when '+\
                'deleting dungeons.'
        sys.exit(1)
    # Get a list of known dungeons and their size.
    if dungeons == []:
        dungeons = listDungeons(world, oworld)
    # No dungeons. Exit.
    if len(dungeons) == 0:
        sys.exit()
    # A list of existing dungeon positions for convenience. 
    existing = set()
    for d in dungeons:
        existing.add((d[0], d[1]))
    # Populate a list of dungeons to delete.
    # If --all was specified, populate the delete list will all known dungeons.
    # Otherwise just validate the -d options. 
    to_delete = []
    if args.all == True:
        for d in dungeons:
            to_delete.append((d[0], d[1]))
    else:
        for d in args.dungeons:
            if (d[0], d[1]) not in existing:
                sys.exit('Unable to locate dungeon at %d %d.'%(d[0], d[1]))
            to_delete.append(d)
    # Build a list of chunks to delete from the dungeon info.
    chunks = []
    # We need to update the caches for the chunks we are affecting
    dcache, dmtime = loadDungeonCache(cache_path)
    ms = mapstore.new(cfg.mapstore)
    for d in to_delete:
        p = [d[0]/16, d[1]/16]
        print 'Deleting dungeon at %d %d...'%(d[0], d[1])
        dkey = '%s,%s' % (d[0],d[1])
        ms.delete_maps(dkey)
        if dkey in dcache:
            del dcache[dkey]
        else:
            print 'WARN: Dungeon not in dungeon cache! '+dkey
        xsize = 0
        zsize = 0
        for e in dungeons:
            if e[0] == d[0] and e[1] == d[1]:
                xsize = e[2]
                zsize = e[3]
                # Hard mode. Delete all chunks.
                if e[4].find('H:1') >= 0:
                    p[0] -= 5
                    p[1] -= 5
                    xsize += 10
                    zsize += 10
                break
        for x in xrange(xsize):
            for z in xrange(zsize):
                chunks.append((p[0]+x, p[1]+z))
    # We need to update the caches for the chunks we are affecting
    ccache, cmtime = loadChunkCache(cache_path)
    # Delete the chunks
    for c in chunks:
        if world.containsChunk(c[0],c[1]):
            world.deleteChunk(c[0],c[1])
            ckey = '%s,%s' % (c[0],c[1])
            if ckey in ccache:
                del ccache[ckey]
            else:
                print 'WARN: Chunk not in chunk cache! '+ckey
    # Save the world.
    print "Saving..."
    world.saveInPlace()
    saveDungeonCache(cache_path, dcache)
    saveChunkCache(cache_path, ccache)
    sys.exit()

# Regenerate mode
if (args.command == 'regenerate'):
    # Get a list of known dungeons and their size.
    dlist = listDungeons(world, oworld)
    # No dungeons. Exit.
    if len(dlist) == 0:
        sys.exit()
    # A list of existing dungeon positions for convenience.
    info = None
    # Find our dungeon
    d = args.dungeon
    for e in dlist:
        if (d[0] == e[0] and d[1] == e[1]):
            info = e
    if info == None:
        sys.exit('Unable to locate dungeon at %d %d.'%(d[0], d[1]))

    # Delete the existing maps for this dungeon so they can be recycled.
    ms = mapstore.new(cfg.mapstore)
    ms.delete_maps('%s,%s'%(d[0], d[1]))

    # Build out our parameters
    # Just build one dungeon
    args.number = 1
    # No seed
    args.seed = None
    # size and levels
    args.x = str(info[2])
    args.z = str(info[3])
    args.levels = str(info[5])
    # Location
    cfg.offset = '%d %d %d'%(info[6], info[7], info[8])
    args.offset = None
    args.bury = None
    # Version 
    version = info[9]
    # Don't bury
    cfg.bury = False
    # Let's not bother with hard mode
    # override it from the config
    cfg.hard_mode = False
    # Entrance offset
    m = re.search('E:(\d+),(\d+)', info[4])
    args.entrance = [int(m.group(1)), int(m.group(2))]
    # Entrance height
    m = re.search('T:(..)', info[4])
    args.entrance_height = int(m.group(1), 16)
    # Write flag
    args.write = True
    #print 'offset:', cfg.offset
    #print 'size:', args.z, args.x, args.levels
    #print 'bury:', cfg.bury
    #print 'hard mode:', cfg.hard_mode
    #print 'entrance:', args.entrance
    # From here, we just go through the add process with the exception that we
    # do not generate ruins.
    print 'Regenerating dungeon at', cfg.offset, '...'


# Everything below is add/regen mode

# Load lewts
loottable.Load()

# Parse out the sizes
min_x = 4
max_x = cfg.max_dist - cfg.min_dist
min_z = 4
max_z = cfg.max_dist - cfg.min_dist
min_levels = 1
max_levels = 8

# Range for Z
result = re.search('(\d+)-(\d+)', args.z)
if (result):
    min_z = int(result.group(1))
    max_z = int(result.group(2))
    args.z = -1
    if (min_z > max_z):
        sys.exit('Minimum Z must be equal or less than maximum Z.')
    if (min_z < 4):
        sys.exit('Minimum Z must be equal or greater than 4.')
# Range for X
result = re.search('(\d+)-(\d+)', args.x)
if (result):
    min_x = int(result.group(1))
    max_x = int(result.group(2))
    args.x = -1
    if (min_x > max_x):
        sys.exit('Minimum X must be equal or less than maximum X.')
    if (min_x < 4):
        sys.exit('Minimum X must be equal or greater than 4.')
# Range for Levels
result = re.search('(\d+)-(\d+)', args.levels)
if (result):
    min_levels = int(result.group(1))
    max_levels = int(result.group(2))
    args.levels = -1
    if (min_levels > max_levels):
        sys.exit('Minimum levels must be equal or less than maximum levels.')
    if (min_levels < 1):
        sys.exit('Minimum levels must be equal or greater than 1.')
    if (max_levels > 42):
        sys.exit('Maximum levels must be equal or less than 42.')
elif int(args.levels) > 0:
    min_levels = int(args.levels)
    max_levels = int(args.levels)

try:
    args.z = int(args.z)
except ValueError:
    sys.exit('Z doesn\'t appear to be an integer!')
try:
    args.x = int(args.x)
except ValueError:
    sys.exit('X doesn\'t appear to be an integer!')
try:
    args.levels = int(args.levels)
except ValueError:
    sys.exit('Levels doesn\'t appear to be an integer!')

if (args.z < 4 and args.z >= 0):
    sys.exit('Too few rooms in Z direction. (%d) Try >= 4.'%(args.z))
if (args.x < 4 and args.x >= 0):
    sys.exit('Too few rooms in X direction. (%d) Try >= 4.'%(args.x))
if (args.levels == 0 or args.levels > 42):
    sys.exit('Invalid number of levels. (%d) Try between 1 and 42.'%(args.levels))

if (args.bury is not None):
    cfg.bury = args.bury

if (args.offset is not None):
    cfg.offset = '%d, %d, %d' % (args.offset[0],
                                 args.offset[1],
                                 args.offset[2])

if (args.entrance is not None and (
    args.entrance[0] >= args.x or
    args.entrance[0] < 0 or
    args.entrance[1] >= args.z or
    args.entrance[1] < 0)):
    print 'Entrance offset values out of range.'
    print 'These should be >= 0 and < the maximum width or length of the dungeon.'
    sys.exit(1)

# Some options don't work with multidungeons
if (args.number is not 1):
    if (args.offset is not None):
        print 'WARN: Offset option is ignored when generating multiple dungeons.'
        cfg.offset = None
    if (args.entrance is not None):
        print 'WARN: Entrance option is ignored when generating multiple dungeons.'
        args.entrance = None
    if  (args.html is not None):
        print 'WARN: HTML option is ignored when generating multiple dungeons.'
        args.html = None
    if  (args.seed is not None):
        print 'WARN: Seed option is ignored when generating multiple dungeons.'
        args.seed = None


print "MCDungeon",__version__,"startup complete. "

if args.debug == True:
    print 'Z:', args.z
    print '   ', min_z
    print '   ', max_z
    print 'X:', args.x
    print '   ', min_x
    print '   ', max_x
    print 'L:', args.levels
    print '   ', min_levels
    print '   ', max_levels

# Look for good chunks
if (cfg.offset is None or cfg.offset is ''):
    # Load the chunk cache
    chunk_cache, chunk_mtime = loadChunkCache(cache_path)
    cached = 0
    notcached = 1

    # Store some stats
    chunk_stats = [
                   ['          Far Chunks', 0],
                   ['         Near Chunks', 0],
                   ['         Unpopulated', 0],
                   ['              Oceans', 0],
                   ['          Structures', 0],
                   ['         High Chunks', 0],
                   ['          Low Chunks', 0],
                   ['         Good Chunks', 0]
                ]
    pm = pmeter.ProgressMeter()
    pm.init(world.chunkCount, label='Finding good chunks:')
    cc = 0
    regions = oworld.get_regionset("overworld")
    chunk_min = None
    chunk_max = None
    for cx, cz, mtime in regions.iterate_chunks():
        cc += 1
        pm.update(cc)
        if args.spawn is not None:
            sx = args.spawn[0]
            sz = args.spawn[1]
        else:
            sx = world.playerSpawnPosition()[0]>>4
            sz = world.playerSpawnPosition()[2]>>4
        # Far chunk
        if (sqrt((cx-sx)*(cx-sx)+(cz-sz)*(cz-sz)) > cfg.max_dist):
            chunk_stats[0][1] += 1
            continue
        # Near chunk
        if (sqrt((cx-sx)*(cx-sx)+(cz-sz)*(cz-sz)) < cfg.min_dist):
            chunk_stats[1][1] += 1
            continue
        # Chunk map stuff
        if chunk_min == None:
            chunk_min = (cx, cz)
        else:
            chunk_min = (min(cx, chunk_min[0]), min(cz, chunk_min[1]))
        if chunk_max == None:
            chunk_max = (cx, cz)
        else:
            chunk_max = (max(cx, chunk_max[0]), max(cz, chunk_max[1]))
        # Check mtime on the chunk to avoid loading the whole thing
        key = '%s,%s' % (cx, cz)
        if (regions.get_chunk_mtime(cx, cz) < chunk_mtime and
            key in chunk_cache):
            cached += 1
        else:
            notcached += 1
            chunk_cache[key] = [None, -1, 0]
            # Load the chunk
            chunk = regions.get_chunk(cx, cz)
            while chunk_cache[key][0] is None:
                # Unpopulated
                if (chunk['TerrainPopulated'] is not 1):
                    chunk_cache[key][0] = 'U'
                    continue
                # Biomes
                chunk_cache[key][1] = numpy.argmax(numpy.bincount((chunk['Biomes'].flatten())))
                # Exclude Oceans
                if chunk_cache[key][1] in [0, 10]:
                    chunk_cache[key][0] = 'O'
                    continue
                # Now the heavy stuff
                # We need to be able to reference the sections in order.
                # for strutures and depths
                b = {}
                for section in sorted(chunk['Sections'],
                                      key=lambda section: section['Y']):
                    b[int(section['Y'])] = section['Blocks']
                # Structures
                if (len(cfg.structure_values) > 0):
                    mats = cfg.structure_values
                    t = False
                    i = 0
                    y = 0
                    while (t == False and y < world.Height//16):
                        if y in b:
                            x = (b[y][:] == mats[i])
                            t = x.any()
                            i += 1
                        if i >= len(mats):
                            y += 1
                            i = 0
                        else:
                            y += 1
                    if t == True:
                        chunk_cache[key][0] = 'S'
                        continue
                # Depths
                min_depth = world.Height
                max_depth = 0
                # list of IDs that are solid. (for our purposes anyway)
                solids = ( 1, 2, 3, 4, 7, 12, 13, 24, 48, 49, 60, 82, 98)
                for x in xrange(16):
                    for z in xrange(16):
                        y = chunk['HeightMap'][z+x*16]-1
                        while (y > 0 and y//16 in b and
                               b[y//16][y%16, z, x] not in solids):
                            y = y - 1
                        min_depth = min(y, min_depth)
                        max_depth = max(y, max_depth)
                # Surface too close to the max height
                if max_depth > world.Height - 27:
                    chunk_cache[key][0] = 'H'
                    continue
                # Surface too close to the bottom of the world
                if min_depth < 12:
                    chunk_cache[key][0] = 'L'
                    continue
                chunk_cache[key][2] = min_depth
                chunk_cache[key][0] = 'G'
        # Classify chunks
        if  chunk_cache[key][0] == 'U':
            chunk_stats[2][1] += 1
        elif  chunk_cache[key][0] == 'O':
            chunk_stats[3][1] += 1
        elif  chunk_cache[key][0] == 'S':
            chunk_stats[4][1] += 1
        elif  chunk_cache[key][0] == 'H':
            chunk_stats[5][1] += 1
        elif  chunk_cache[key][0] == 'L':
            chunk_stats[6][1] += 1
        else:
            chunk_stats[7][1] += 1
            good_chunks[(cx, cz)] = chunk_cache[key][2]
    pm.set_complete()

    # Find old dungeons
    old_dungeons = listDungeons(world, oworld, expand_hard_mode=True)
    for d in old_dungeons:
        if args.debug: print 'old dungeon:', d
        p = (d[0]/16, d[1]/16)
        for x in xrange(int(d[2])):
            for z in xrange(int(d[3])):
                if (p[0]+x,p[1]+z) in good_chunks:
                    del(good_chunks[(p[0]+x,p[1]+z)])
                    key = '%s,%s' % (p[0]+x,p[1]+z)
                    chunk_cache[key] = ['S', -1, 0]
                    chunk_stats[4][1] += 1
                    chunk_stats[7][1] -= 1

    # Funky little chunk map
    if args.debug:
        for cz in xrange(chunk_min[1], chunk_max[1]+1):
            for cx in xrange(chunk_min[0], chunk_max[0]+1):
                key = '%s,%s' % (cx,cz)
                if key in chunk_cache:
                    if chunk_cache[key][0] == 'U':
                        sys.stdout.write(materials.RED)
                    if chunk_cache[key][0] == 'O':
                        sys.stdout.write(materials.BLUE)
                    if chunk_cache[key][0] == 'S':
                        sys.stdout.write(materials.DGREY)
                    if chunk_cache[key][0] == 'H':
                        sys.stdout.write(materials.PURPLE)
                    if chunk_cache[key][0] == 'L':
                        sys.stdout.write(materials.PURPLE)
                    if chunk_cache[key][0] == 'G':
                        sys.stdout.write(materials.GREEN)
                    sys.stdout.write(chunk_cache[key][0])
                    sys.stdout.write(chunk_cache[key][0])
                    sys.stdout.write(materials.ENDC)
                else:
                    sys.stdout.write('  ')
            print

    # Re-cache the chunks and update mtime
    saveChunkCache(cache_path, chunk_cache)

    for stat in chunk_stats:
        print '   %s: %d'%(stat[0], stat[1])
    print ' Cache hit rate: %d/%d (%d%%)' % (cached, notcached+cached,
                                             100*cached/(notcached+cached))


# Load the cache for updates later.
dungeonCache, mtime = loadDungeonCache(cache_path)
while args.number is not 0:
    # Define our dungeon.
    x = args.x
    z = args.z
    levels = args.levels
    if (args.z < 0):
        z = randint(min_z, max_z)
    if (args.x < 0):
        x = randint(min_x, max_x)
    if (args.levels < 0):
        levels = randint(min_levels, max_levels)

    dungeon = None
    located = False

    if (cfg.offset is not None and cfg.offset is not ''):
        pos = str2Vec(cfg.offset)
        pos.x = pos.x &~15
        pos.z = pos.z &~15
        dungeon = Dungeon(x, z, levels, good_chunks, args, world, oworld,
                          chunk_cache)
        print 'Dungeon size: %d x %d x %d' % (x, z, levels)
        dungeon.position = pos
        if (cfg.bury is False):
            located = dungeon.bury(world, manual=True)
            located = True
        else:
            located = dungeon.bury(world)
            if (located == False):
                print 'Unable to bury a dungeon of requested depth at', pos
                print 'Try fewer levels, or a smaller size, or another location.'
                sys.exit(1)
        print "Location set to: ", dungeon.position

    else:
        print "Searching for a suitable location..."
        while (located is False):
            dungeon = Dungeon(x, z, levels, good_chunks, args, world, oworld,
                              chunk_cache)
            located = dungeon.findlocation(world, dungeon_positions)
            if (located is False):
                adjusted = False
                if (args.x < 0 and x > min_x):
                    x -= 1
                    adjusted = True
                if (args.z < 0 and z > min_z):
                    z -= 1
                    adjusted = True
                if (adjusted is False and
                    args.levels < 0 and
                    levels > min_levels):
                    levels -= 1
                    adjusted = True
                if (adjusted is False):
                    print 'Unable to place any more dungeons.'
                    break
            else:
                print 'Dungeon size: %d x %d x %d' % (x, z, levels)
                print "Location: ", dungeon.position
    if (located is True):
        if (args.seed is not None):
            seed(args.seed)
            print 'Seed:',args.seed

        print "Generating rooms..."
        dungeon.genrooms(args.entrance)

        print "Generating halls..."
        dungeon.genhalls()

        print "Generating floors..."
        dungeon.genfloors()

        print "Generating features..."
        dungeon.genfeatures()

        if args.command != 'regenerate':
            print "Generating ruins..."
            dungeon.genruins(world)
            dungeon.setentrance(world)
        else:
            dungeon.entrance.height = args.entrance_height

        print "Finding secret rooms..."
        dungeon.findsecretrooms()

        dungeon.renderrooms()

        dungeon.renderhalls()

        dungeon.renderfloors()

        dungeon.renderfeatures()

        print "Rendering hall traps..."
        dungeon.renderhallpistons()

        dungeon.renderruins()

        dungeon.processBiomes()

        print "Placing doors..."
        dungeon.placedoors(cfg.doors)

        print "Placing portcullises..."
        dungeon.placeportcullises(cfg.portcullises)

        print "Placing torches..."
        dungeon.placetorches()

        print "Placing chests..."
        dungeon.placechests()

        print "Placing spawners..."
        dungeon.placespawners()

        # Signature
        flags = 'H:'
        if cfg.hard_mode:
            flags += '1'
        else:
            flags += '0'
        flags += ';E:%d,%d'%(dungeon.entrance_pos.x, dungeon.entrance_pos.z)
        flags += ';T:%.2x'%dungeon.entrance.height
        dungeon.setblock(Vec(0,0,0), materials.WallSign, 4, hide=True)
        dungeon.addsign(Vec(0,0,0),
                        '[MCD]'+__version__,
                        str(int(time.time())),
                        '%d,%d,%d'%(dungeon.xsize,
                                    dungeon.zsize,
                                    dungeon.levels),
                        flags)
        dungeon.setblock(Vec(1,0,0), materials.Stone, hide=True)

        # Generate maps
        if (args.write and cfg.maps > 0):
            print "Generating maps..."
            ms = mapstore.new(cfg.mapstore)
            for level in xrange(1, dungeon.levels+1):
                if randint(1, 100) > cfg.maps:
                    next
                m = ms.generate_map(dungeon, level)
                for loc in dungeon.tile_ents.keys():
                    ent = dungeon.tile_ents[loc]
                    # Place the map in chests that are one level less than
                    # the map, or in the case of level 1, above ground.
                    if (ent['id'].value == 'Chest' and
                        (loc.y//dungeon.room_height == level-2 or
                        (loc.y < 0 and level == 1))):
                        if not dungeon.addchestitem_tag(loc, m):
                            print 'WARNING: Unable to add map to chest'
                        else:
                            break

        # Write the changes to the world.
        dungeon.applychanges(world)

        # Output an html version.
        if (args.html is not None):
            dungeon.outputhtml(args.html, args.force)

        # Output a slice of the dungeon to the terminal if requested.
        if (args.term is not None):
            dungeon.outputterminal(args.term)

        start = dungeon.position
        end = Vec(start.x + dungeon.xsize * dungeon.room_size - 1,
          start.y - dungeon.levels * dungeon.room_height + 1,
          start.z + dungeon.zsize * dungeon.room_size - 1)
        dungeon_positions[Vec(start.x>>4,
                             0,
                             start.z>>4)] = start
        dungeons.append('Dungeon %d (%d x %d x %d): %s to %s' %
                        (len(dungeons)+1,
                         x,
                         z,
                         levels,
                         str(start),
                         str(end)))
        total_rooms += (x * z * levels)

        # Update the cache
        key = '%s,%s' % (dungeon.position.x, dungeon.position.z)
        dungeonCache[key] = 1

    args.number -= 1
    if (located is False):
        args.number = 0

if (len(dungeons) == 0):
    print 'No dungeons were generated!'
    print 'You may have requested too deep or too large a dungeon, or your '
    print 'allowed spawn region is too small. If using hard mode, remember '
    print 'to add 10 chunks in each direction to the size of your dungeon.'
    print 'Check min_dist, max_dist, and hard_mode settings in your config.'
    sys.exit(1)

# Relight
if (args.write is True and args.skiprelight is False):
    class myHandler(object):
        _curr = 34
        _count = 0
        def __init__(self):
            self.pm = pmeter.ProgressMeter()
            self.pm.init(self._curr, label='Relighting chunks:')
            #self.pm.update_left(self._curr)

        def write(self, buff=''):
            #self._count += 1
            #print self._count
            self._curr -= 1
            self.pm.update_left(self._curr)

        def flush(self):
            pass

        def done(self):
            self.pm.set_complete()

    # This is super ugly but, dammit, I want progress bars!
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    h = myHandler()
    logging.basicConfig(stream=h, level=logging.INFO)
    world.generateLights()
    h.done()
    logging.getLogger().level = logging.CRITICAL
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

print 'Placed', len(dungeons), 'dungeons!'
for d in dungeons:
    print d
print 'Total rooms:', total_rooms

# Save the world.
if (args.write is True):
    print "Saving..."
    world.saveInPlace()
    saveDungeonCache(cache_path, dungeonCache)
else:
    print "Map NOT saved! This was a dry run. Use --write to enable saving."
