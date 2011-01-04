"""
@author Dorian Raymer
@author Michael Meisinger
@brief Python Capability Container shell
"""

import os
import re
import sys 
import tty
import termios
import rlcompleter

from twisted.internet import stdio
from twisted.conch.insults import insults
from twisted.conch import manhole
from twisted.python import text

from ion.core import ionconst

CTRL_A = '\x01'
CTRL_E = '\x05'
CTRL_R = "\x12"
ESC = "\x1b"

def get_virtualenv():
    if 'VIRTUAL_ENV' in os.environ:
        virtual_env = os.path.join(os.environ.get('VIRTUAL_ENV'),
                        'lib',
                        'python%d.%d' % sys.version_info[:2],
                        'site-packages')
        return "[env: %s]" % virtual_env
    return "[env: system]"


class PreparseredInterpreter(manhole.ManholeInterpreter):
    """
    """

    def push(self, line):
        """
        pre parse input lines
        """
        if line and line[-1] == '?':
            line = 'obj_info(%s)' % line[:-1]
        return manhole.ManholeInterpreter.push(self, line)


#class ConsoleManhole(manhole.ColoredManhole):
class ConsoleManhole(manhole.Manhole):
    ps = ('><> ', '... ')

    def initializeScreen(self):
        """@todo This should show relevant and useful development info:
         - python version
         - dependencies
          o versions
          o install path
         - virtualenv (if used)

        @todo Dependency info will be listed in the setup file
        """
        # self.terminal.reset()
        self.terminal.write('\r\n')
        self.terminal.write('ION Python Capability Container (version %s)\r\n' % (ionconst.VERSION))
        self.terminal.write('%s \r\n' % get_virtualenv())
        self.terminal.write('[container id: %s@%s.%d] \r\n' % (os.getlogin(), os.uname()[1], os.getpid()))
        self.terminal.write('\r\n')
        self.terminal.write(self.ps[self.pn])
        self.setInsertMode()

        self.historysearch = False
        self.historysearchbuffer = []
        self.historyFail = False

    def handle_TAB(self):
        completer = rlcompleter.Completer(self.namespace)
        head_line, tail_line = self.currentLineBuffer()
        search_line = head_line
        cur_buffer = self.lineBuffer
        cur_index = self.lineBufferIndex

        completer = rlcompleter.Completer(self.namespace)

        def find_term(line):
            chrs = []
            attr = False
            for c in reversed(line):
                if c == '.':
                    attr = True
                if not c.isalnum() and c not in ('_', '.'):
                    break
                chrs.insert(0, c)
            return ''.join(chrs), attr

        search_term, attrQ = find_term(search_line)

        if not search_term:
            return manhole.Manhole.handle_TAB(self)        

        if attrQ:
            matches = completer.attr_matches(search_term)
            matches = list(set(matches))
            matches.sort()
        else:
            matches = completer.global_matches(search_term)

        def same(*args):
            if len(set(args)) == 1:
                return args[0]
            return False

        def progress(rem):
            letters = []
            while True:
                letter = same(*[elm.pop(0) for elm in rem if elm])
                if letter:
                    letters.append(letter)
                else:
                    return letters

        if matches is not None:
            rem = [list(s.partition(search_term)[2]) for s in matches]
            more_letters = progress(rem)
            n = len(more_letters)
            lineBuffer = list(head_line) + more_letters + list(tail_line)
            if len(matches) > 1:
                match_str = "%s \t\t" * len(matches) % tuple(matches)
                match_rows = text.greedyWrap(match_str)
                line = self.lineBuffer
                self.terminal.nextLine()
                self.terminal.saveCursor()
                for row in match_rows:
                    self.addOutput(row, True)
                if tail_line:
                    self.terminal.cursorBackward(len(tail_line))
                    self.lineBufferIndex -= len(tail_line)
            self._deliverBuffer(more_letters)



    # def handle_INT(self):

    def handle_QUIT(self):
        self.terminal.write('Bye!')
        # write reset to terminal before connection close OR
        # use os.write to fd method below?
        # self.terminal.write("\r\x1bc\r")
        self.terminal.loseConnection()
        # os.write(fd, "\r\x1bc\r")
        # then what?

    def connectionLost(self, reason):

        # save the last 2500 lines of history to the history buffer
        if not self.namespace['cc'].config['no_history']:
            try:
                outhistory = "\n".join(self.historyLines[-2500:])

                f = open(os.path.join(os.environ["HOME"], '.cchistory'), 'w')
                f.writelines(outhistory)
                f.close()
            except (IOError, TypeError):
                # i've seen sporadic TypeErrors when joining the history lines - complaining
                # about seeing a list when expecting a string. Can't figure out how to reproduce
                # it consistently, but it deals with exiting the shell just after an error in the
                # REPL. In any case, don't worry about it, and don't clobber history.
                pass

        self.factory.stop()

    def handle_CTRLR(self):
        if self.historysearch:
            self.findNextMatch()
        else:
            self.historysearch = True
        self.printHistorySearch()

    def handle_RETURN(self):
        self.stopHistorySearch()
        manhole.Manhole.handle_RETURN(self)

    def handle_BACKSPACE(self):
        if self.historysearch:
            if len(self.historysearchbuffer):
                self.historyFail = False
                self.historysearchbuffer.pop()
                self.printHistorySearch()
            # should vbeep on else here
        else:
            manhole.Manhole.handle_BACKSPACE(self)

    def handle_UP(self):
        self.stopHistorySearch()
        manhole.Manhole.handle_UP(self)

    def handle_DOWN(self):
        self.stopHistorySearch()
        manhole.Manhole.handle_DOWN(self)

    def handle_INT(self):
        self.stopHistorySearch()
        self.historyPosition = len(self.historyLines)
        manhole.Manhole.handle_INT(self)

    def handle_RIGHT(self):
        self.stopHistorySearch()
        manhole.Manhole.handle_RIGHT(self)

    def handle_LEFT(self):
        self.stopHistorySearch()
        manhole.Manhole.handle_LEFT(self)

    def handle_ESC(self):
        self.stopHistorySearch()

    def stopHistorySearch(self):
        wassearch = self.historysearch
        self.historysearch = False
        self.historysearchbuffer = []
        if wassearch:
            self.printHistorySearch()

    def printHistorySearch(self):
        self.terminal.saveCursor()
        self.terminal.index()
        self.terminal.write('\r')
        self.terminal.cursorPos.x = 0
        self.terminal.eraseLine()
        if self.historysearch:
            if self.historyFail:
                self.addOutput("failing-")
            self.addOutput("history-search: " + "".join(self.historysearchbuffer) + "_")
        self.terminal.restoreCursor()

    def findNextMatch(self):
        # search from history search pos to 0, uninclusive

        historyslice = self.historyLines[:self.historyPosition-1]
        cursearch = ''.join(self.historysearchbuffer)

        foundone = False
        historyslice.reverse()
        for i in range(len(historyslice)):
            line = historyslice[i]
            if cursearch in line:
                self.historyPosition = len(historyslice) - i
                self.historysearch = False

                if self.lineBufferIndex > 0:
                    self.terminal.cursorBackward(self.lineBufferIndex)
                self.terminal.eraseToLineEnd()

                self.lineBuffer = []
                self.lineBufferIndex = 0
                self._deliverBuffer(line)

                # set x to matching coordinate
                matchidx = line.index(cursearch)
                self.terminal.cursorBackward(self.lineBufferIndex - matchidx)
                self.lineBufferIndex = matchidx

                self.historysearch = True
                foundone = True
                break

        if not foundone:
            self.historyFail = True

    def characterReceived(self, ch, moreCharactersComing):
        if self.historysearch:
            self.historyFail = False
            self.historyPosition = len(self.historyLines)
            self.historysearchbuffer.append(ch)
            self.findNextMatch()
            self.printHistorySearch()
        else:
            manhole.Manhole.characterReceived(self, ch, moreCharactersComing)

    def connectionMade(self):
        manhole.Manhole.connectionMade(self)
        self.interpreter = PreparseredInterpreter(self, self.namespace)

        self.keyHandlers.update({
            CTRL_A: self.handle_HOME,
            CTRL_E: self.handle_END,
            CTRL_R: self.handle_CTRLR,
            ESC: self.handle_ESC,
            })

        # read in history from history file on disk, set internal history/position
        if not self.namespace['cc'].config['no_history']:
            try:
                f = open(os.path.join(os.environ["HOME"], '.cchistory'), 'r')
                for line in f:
                    self.historyLines.append(line.rstrip('\n'))

                f.close()

                self.historyPosition = len(self.historyLines)
            except IOError:
                pass

def makeNamespace():
    from ion.core.cc.shell_api import send, ps, ms, spawn, kill, info, rpc_send, svc, nodes, identify
    from ion.core.id import Id

    def obj_info(item, format='print'):
        """Print useful information about item."""
        if item == '?':
            print 'Type <object>? for info on that object.'
            return
        _name = 'N/A'
        _class = 'N/A'
        _doc = 'No Documentation.'
        if hasattr(item, '__name__'):
            _name = item.__name__
        if hasattr(item, '__class__'):
            _class = item.__class__.__name__
        _id = id(item)
        _type = type(item)
        _repr = repr(item)
        if callable(item):
            _callable = "Yes"
        else:
            _callable = "No"
        if hasattr(item, '__doc__'):
            maybe_doc = getattr(item, '__doc__')
            if maybe_doc:
                _doc = maybe_doc
            _doc = _doc.strip()   # Remove leading/trailing whitespace.
        info = {'name':_name, 'class':_class, 'type':_type, 'repr':_repr, 'doc':_doc}
        if format is 'print':
            for k,v in info.iteritems():
                print k.capitalize(),': ', v
            print '\n\n'
            return
        elif format is 'dict':
            return info

    namespace = locals()
    return namespace

class Control(object):

    fd = None
    serverProtocol = None
    oldSettings = None

    # A dict with the locals() of the shell, once started
    namespace = None
    # A dict to collect the shell variables before shell is started
    pre_namespace = {}

    def start(self, ccService):
        fd = sys.__stdin__.fileno()
        fdout = sys.__stdout__.fileno()

        self.oldSettings = termios.tcgetattr(fd)
        # tty.setraw(fd)
        tty.setraw(fd, termios.TCSANOW) # when=now
        self.fd = fd

        # stdout fd
        outSettings = termios.tcgetattr(fdout)
        outSettings[1] = termios.OPOST | termios.ONLCR
        termios.tcsetattr(fdout, termios.TCSANOW, outSettings)

        namespace = makeNamespace()

        serverProtocol = insults.ServerProtocol(ConsoleManhole, namespace)
        serverProtocol.factory = self
        self.serverProtocol = serverProtocol

        namespace['control'] = self
        namespace['cc'] = ccService
        namespace['tsp'] = serverProtocol
        namespace.update(self.pre_namespace)

        stdio.StandardIO(serverProtocol)
        self.namespace = self.serverProtocol.terminalProtocol.namespace
        from ion.core.cc import shell_api
        shell_api.namespace = self.namespace
        shell_api._update()

    def stop(self):
        termios.tcsetattr(self.fd, termios.TCSANOW, self.oldSettings)
        # if terminal write reset doesnt work in handle QUIT, use this
        os.write(self.fd, "\r\x1bc\r")
        os.write(self.fd, 'Shell exited. Press Ctrl-c to stop container\n')

    def add_term_name(self, key, value):
        if self.namespace:
            self.namespace[key] = value
        else:
            self.pre_namespace[key] = value

try:
    control
except NameError:
    control = Control()

