#!/usr/bin/python
# by Hubert Chathi, 2007, 2008
# This file is hereby placed in the public domain.  Feel free to modify
# and redistribute at will.
# (Note, however, that python-jabberbot, which this file depends on, is
# licensed under the GNU GPL v3 or later, and xmppy is licensed under the
# GNU GPL v2 or later.)

import xmpp
import os
import jabberbot
import subprocess
from ConfigParser import RawConfigParser

class SystemBot(jabberbot.JabberBot):
    def bot_exec(self, mess, args):
    	"""Executes the given command"""
	if args.strip() == '':
		return 'needs arguments'
	else:
		try:
			return subprocess.Popen(args.split(), stdout=subprocess.PIPE).communicate()[0]
		except Exception, e:
			return e

    def bot_who(self, mess, args):
        """Display who's currently logged in."""
        who_pipe = os.popen('/usr/bin/who', 'r')
        who = who_pipe.read().strip()
        who_pipe.close()

        return who

    def idle_proc(self):
        status = []

        load = 'load average: %s %s %s' % os.getloadavg()
        status.append(load)

        # calculate the uptime
        uptime_file = open('/proc/uptime')
        uptime = uptime_file.readline().split()[0]
        uptime_file.close()

        uptime = float(uptime)
        (uptime,secs) = (int(uptime / 60), uptime % 60)
        (uptime,mins) = divmod(uptime,60)
        (days,hours) = divmod(uptime,24)

        uptime = 'uptime: %d day%s, %d:%02d' % (days, days != 1 and 's' or '', hours, mins)
        status.append(uptime)

        # calculate memory and swap usage
        meminfo_file = open('/proc/meminfo')
        meminfo = {}
        for x in meminfo_file:
            try:
                (key,value,junk) = x.split(None, 2)
                key = key[:-1] # strip off the trailing ':'
                meminfo[key] = int(value)
            except:
                pass
        meminfo_file.close()

        memusage = 'Memory used: %d of %d kB (%d%%) - %d kB free' \
                   % (meminfo['MemTotal']-meminfo['MemFree'],
                      meminfo['MemTotal'],
                      100 - (100*meminfo['MemFree']/meminfo['MemTotal']),
                      meminfo['MemFree'])
        status.append(memusage)
        if meminfo['SwapTotal']:
            swapusage = 'Swap used: %d of %d kB (%d%%) - %d kB free' \
                      % (meminfo['SwapTotal']-meminfo['SwapFree'],
                         meminfo['SwapTotal'],
                         100 - (100*meminfo['SwapFree']/meminfo['SwapTotal']),
                         meminfo['SwapFree'])
            status.append(swapusage)

        status = '\n'.join(status)
        # TODO: set "show" based on load? e.g. > 1 means "away"
        if not hasattr(self, 'laststatus') or self.laststatus != status:
            self.conn.send(xmpp.Presence(status=status))
            self.laststatus = status
        return

config = RawConfigParser()
config.read(['/etc/systembot.cfg','systembot.cfg'])

bot = SystemBot(config.get('systembot','username'),
                config.get('systembot','password'))
bot.serve_forever()
