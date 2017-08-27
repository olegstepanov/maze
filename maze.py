import curses
import random
import time

current_time = lambda: int(round(time.time() * 1000))

def init_curses():
    stdscr = curses.initscr()
    curses.start_color()
    curses.use_default_colors()
    curses.noecho()
    curses.cbreak()

    stdscr.keypad(1)

    for i in range(0, curses.COLORS):
        curses.init_pair(i, i, -1)

    return stdscr

class Break(Exception): pass

class Dead(Exception): pass

class ObjectTypes:
    Player, Monster, Health, Bullet = range(4)

class Direction:
    Up, Down, Left, Right = range(4)

class Object:
    health = 0
    c = -1
    l = -1
    type = ObjectTypes.Monster
    last_direction = Direction.Right

    def __init__(self, c, l, type, health=0):
        self.type = type
        self.health = health
        self.c = c
        self.l = l

    def _health_color(self):
        if self.health == 1:
            return curses.color_pair(curses.COLOR_RED)
        elif self.health == 2:
            return curses.color_pair(curses.COLOR_YELLOW)
        elif self.health == 3:
            return curses.color_pair(curses.COLOR_GREEN)

    def strike(self):
        self.health = self.health - 1
        if self.health == 0:
            self.die()

    def die(self):
        objects.remove(self)

        if self.type == ObjectTypes.Player:
            raise Dead

    def collide(self, other):
        if self.is_creature() and other.is_creature():
            if random.random() > 0.5:
                self.strike()
            else:
                other.strike()
            return self.health == 0
        elif self.is_creature() and other.type == ObjectTypes.Bullet:
            self.strike()
        if self.type == ObjectTypes.Health and other.is_creature():
            other.health = 3

    def is_creature(self):
        return self.type in [ObjectTypes.Monster, ObjectTypes.Player]

    def write(self, scr):
        if self.type == ObjectTypes.Player:
            scr.addch('@', self._health_color() | curses.A_BOLD)
        elif self.type == ObjectTypes.Health:
            scr.addch('$', curses.color_pair(curses.COLOR_WHITE) | curses.A_BOLD)
        elif self.type == ObjectTypes.Monster:
            scr.addch('!', self._health_color() | curses.A_BOLD)
        elif self.type == ObjectTypes.Bullet:
            scr.addch('*', self._health_color() | curses.A_BOLD)
        else:
            scr.addch(' ')


class CellTypes:
    Wall, Space = range(2)


class Cell:
    def __init__(self, type, object=None):
        self.type = type
        self.object = object
        self.health = 3

    def _health_color(self):
        if self.health == 1:
            return curses.color_pair(curses.COLOR_RED)
        elif self.health == 2:
            return curses.color_pair(curses.COLOR_YELLOW)
        elif self.health == 3:
            return curses.color_pair(curses.COLOR_CYAN)

    def write(self, scr):
        if self.type == CellTypes.Wall:
            scr.addch('#', self._health_color())
        else:
            scr.addch(' ')

map = []
objects = []
player = None
step_length = 300
time_limit = 99 * 60 * 1000

def load_map():
    global player

    l = 0
    with open('maze.txt', 'r') as mf:
        tmap = mf.readlines()
        for tline in tmap:
            line = []
            c = 0
            for tcell in tline.rstrip('\n'):
                if tcell == '#':
                    line.append(Cell(CellTypes.Wall))
                else:
                    line.append(Cell(CellTypes.Space))

                    if tcell == '@':
                        player = Object(c, l, ObjectTypes.Player, 3)
                        objects.append(player)
                    elif tcell == '$':
                        objects.append(Object(c, l, ObjectTypes.Health, 3))
                    elif '0' <= tcell <= '9':
                        objects.append(Object(c, l, ObjectTypes.Monster, 3))

                c = c + 1
            map.append(line)
            l = l + 1
    return map


def dig(l, c, dir):
    dl, dc = get_new_coords(l, c, dir)
    if not inside_map(dl, dc):
        return
    if map[dl][dc].type == CellTypes.Wall:
        map[dl][dc] = Cell(CellTypes.Space)
        for t in range(0, 2):
            dig(dl, dc, random.randint(0, 3))

def generate_map(ls, cs):
    global player

    for l in range(0, ls):
        line = []
        for c in range(0, cs):
            line.append(Cell(CellTypes.Wall))
        map.append(line)

    i = 0

    while i < 10:
        pl = random.randint(1, ls - 1)
        pc = random.randint(1, cs - 1)
        map[pl][pc] = Cell(CellTypes.Space)
        object = Object(pc, pl, ObjectTypes.Player if i == 0 else ObjectTypes.Monster, health=3)
        objects.append(object)

        if i == 0:
            player = object

        for t in range(0, 3):
            dig(pl, pc, random.randint(0, 3))

        i+=1


def draw_map(scr):
    scr.erase()

    game_time = (time_limit - (current_time() - start_time)) / 1000
    scr.addstr(0, 0, '%02d:%02d'%(game_time / 60, game_time % 60))

    map_offset_l = 1
    map_offset_c = 0

    lineno = 0
    for line in map:
        scr.move(map_offset_l + lineno, map_offset_c + 0)
        for cell in line:
            cell.write(scr)
        lineno = lineno + 1

    for o in objects:
        scr.move(map_offset_l + o.l, map_offset_c + o.c)
        o.write(scr)

    scr.refresh()

def move_monster(o):
    while not move_object(o, random.randint(0, 3)):
        pass

def move_bullet(o):
    if not move_object(o, o.last_direction):
        objects.remove(o)

def move_player(dir):
    move_object(player, dir)

def get_new_coords(l, c, dir):
    if dir == Direction.Up:
        l = l - 1
    elif dir == Direction.Down:
        l = l + 1
    elif dir == Direction.Left:
        c = c - 1
    elif dir == Direction.Right:
        c = c + 1

    return l, c

def move_object(obj, dir):
    l, c = get_new_coords(obj.l, obj.c, dir)
    if not inside_map(l, c):
        return False

    if map[l][c].type != CellTypes.Space:
        if obj.type == ObjectTypes.Bullet:
            decay(l, c)
        return False

    for o in objects:
        if o == obj:
            continue
        elif o.c == c and o.l == l:
            if not o.collide(obj):
                return True
            else:
                break

    obj.c = c
    obj.l = l
    obj.last_direction = dir

    return True

def inside_map(l, c):
    return not (l < 0 or l >= len(map) or c < 0 or c >= len(map[0]))

def evolve_map():
    for l in range(0, len(map)):
        for c in range(0, len(map[0])):
            cell = map[l][c]
            if cell.type == CellTypes.Wall and cell.health < 3:
                decay(l, c)
                decay(l - 1, c)
                decay(l + 1, c)
                decay(l - 1, c - 1)
                decay(l + 1, c - 1)
                decay(l - 1, c + 1)
                decay(l + 1, c + 1)
                decay(l, c - 1)
                decay(l, c + 1)

def decay(l, c):
    if not inside_map(l, c): return

    cell = map[l][c]

    if cell.type == CellTypes.Wall:
        cell.health -= 1
        if cell.health == 0:
            map[l][c] = Cell(CellTypes.Space)
    else:
        for o in objects:
            if o.c == c and o.l == l and o.is_creature():
                o.strike()

def fire():
    bullet = Object(player.c, player.l, ObjectTypes.Bullet, 3)
    bullet.last_direction = player.last_direction
    objects.append(bullet)

class ControlMode:
    Movement, Console = range(2)

control_mode = ControlMode.Movement
generate_map(40, 80)
stdscr = init_curses()
stdscr.nodelay(1)
start_time = current_time()
command = ""

def mode_movement():
    global control_mode
    global command
    control_mode = ControlMode.Movement
    command = ""
    curses.curs_set(0)
    pass

def mode_console():
    global control_mode
    global command
    control_mode = ControlMode.Console
    command = ""
    curses.curs_set(1)
    pass

def process_command(command):
    if command == "quit":
        return False
    elif command == "heal":
        player.health = 3
    return True

try:
    prev_time = current_time()
    mode_movement()

    while True:
        if current_time() - prev_time > step_length:
            for o in objects:
                if o.type == ObjectTypes.Monster:
                    move_monster(o)
                elif o.type == ObjectTypes.Bullet:
                    move_bullet(o)
            evolve_map()
            prev_time = current_time()

        draw_map(stdscr)
        if control_mode == ControlMode.Console:
            command_string = '> %s' % (command)
            stdscr.addstr(0, 0, command_string)
            pass

        c = stdscr.getch()

        if c == ord('/'):
            if control_mode == ControlMode.Movement:
                mode_console()
            elif control_mode == ControlMode.Console:
                mode_movement()
            continue

        if control_mode == ControlMode.Movement:
            if c == ord('q'):
                break
            elif c == curses.KEY_LEFT:
                move_player(Direction.Left)
            elif c == curses.KEY_RIGHT:
                move_player(Direction.Right)
            elif c == curses.KEY_UP:
                move_player(Direction.Up)
            elif c == curses.KEY_DOWN:
                move_player(Direction.Down)
            elif c == ord(' '):
                fire()
        elif control_mode == ControlMode.Console:
            if ord('a') <= c <= ord('z'):
                command += chr(c)
            elif c == curses.KEY_BACKSPACE:
                command = command[:-2]
            elif c == curses.KEY_ENTER or c == 10 or c == 13:
                if not process_command(command):
                    break
                mode_movement()


except Dead:
    print('You\'re Dead!')

curses.nocbreak()
stdscr.keypad(0)
curses.echo()
curses.endwin()
