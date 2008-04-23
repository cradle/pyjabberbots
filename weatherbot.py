#!/usr/bin/python
"""Weather bot for Jabber

Fetches weather data from a variety of sources, for access via Jabber.

http://www.uhoreg.ca/programming/jabberbots

TODO:
- catch signals
- The Weather Network
- better exception handling
- DISCO
- weather.uwaterloo.ca
- user avatars?
"""

__version__ = "0.2.alpha"
__license__ = """Copyright 2007-2008 Hubert Chathi <hubert@uhoreg.ca>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA."""

__author__ = "Hubert Chathi <hubert@uhoreg.ca>"

import time
import urllib
import xmpp
from xml.dom import minidom
from os import path
try:
    import cPickle as pickle
except:
    import pickle
import errno
import threading
import random
from ConfigParser import RawConfigParser

random.seed()

class WeatherFetcherExample:
    """Prototype weather fetcher class

    Each class must implement a "refresh" method, and have a "commands" member
    variable.  The commands member variable should be a list of commands that
    the bot responds to.  For each command listed, the class should either have
    a method named "handle_xxx(self, conn, msg)", "get_xxx(self, msg)", or a
    variable named "xxx".  (They are searched in that order.)

    The class must have a "presence" variable.

    The class must also have a "refresh_test(self, time)" method or an
    "update_time" variable.
    """
    def refresh(self):
        pass

    commands = ['list of commands that the bot responds to']

    def handle_xxx(self, conn, msg):
        """Handle the xxx message from the user.
        "conn" is the xmpp.dispatcher.Dispatcher object.
        "msg" is the xmpp.Protocol object.
        """
        pass

    def get_xxx(self, msg):
        pass

    xxx = 'the contents of the message that the bot should respond with when the user issues the command "xxx"'
    xxx_help = 'the help message to display for the "xxx" command'

    presence = xmpp.protocol.Presence(status='XMPP presence for the bot')

    def refresh_test(self, time):
        """Return True if the bot should be refreshed at the given time."""
        pass

    update_time = 'the time of the next update'


def random_periodic_update_time (offset=5, frequency=1, maxrand=5):
    """Returns a random update time for periodic updates.
    """
    now = time.time()
    base = 3600/frequency
    return now + base - (now % base) + offset*60 + random.randint(0,maxrand*60)


class YahooWeather:
    """Get weather data from Yahoo! Weather <http://weather.yahoo.com>

    Detailed information on Yahoo!'s weather feeds can be found at:
    http://developer.yahoo.com/weather/
    """
    def __init__(self,opts):
        self.url = 'http://weather.yahooapis.com/forecastrss?p=%s' % opts['location']
        if opts.has_key('units'):
            self.url += '&u=%s' % opts['units']

    commands = ['forecast', 'info']
    forecast_help = 'displays the current forecast'
    info_help = 'displays information on this weather feed'

    def refresh(self):
        fp = urllib.urlopen(self.url)
        doc = minidom.parse(fp)
        fp.close()

        units = doc.getElementsByTagName('yweather:units')[0]
        temperature_units = units.getAttribute('temperature')
        distance_units = units.getAttribute('distance')
        pressure_units = units.getAttribute('pressure')
        speed_units = units.getAttribute('speed')

        try:
            conditions = doc.getElementsByTagName('yweather:condition')[0]
            conditions_text = "%s, %s %s (%s)" % (conditions.getAttribute('text'), conditions.getAttribute('temp'), temperature_units, conditions.getAttribute('date'))
        except:
            conditions_text = '[no data]'

        try:
            # FIXME: convert wind direction into some thing human-readable
            wind = doc.getElementsByTagName('yweather:wind')[0]
            wind_text = 'Wind chill: %s %s; Wind: %s %s, %s' % (wind.getAttribute('chill'), temperature_units, wind.getAttribute('speed'), speed_units, wind.getAttribute('direction'))
        except:
            wind_text = 'Wind: [no data]'

        try:
            atmosphere = doc.getElementsByTagName('yweather:atmosphere')[0]
            atmosphere_text = 'Presure: %s %s %s\nHumidity: %s%%\nVisibility: %s %s\n' \
                              % (atmosphere.getAttribute('pressure'), pressure_units, ['steady', 'rising', 'falling'][int(atmosphere.getAttribute('rising'))],
                                 atmosphere.getAttribute('humidity'),
                                 atmosphere.getAttribute('visibility'), distance_units)
        except:
            atmosphere_text = 'Pressure: [no data]\nHumidity: [no data]\nVisibility: [no data]'

        status = """%s
%s
%s
Yahoo! Weather: <http://weather.yahoo.com>""" % (conditions_text, wind_text, atmosphere_text)

        self.presence = xmpp.protocol.Presence(status=status)

        forecast = []
        for x in doc.getElementsByTagName('yweather:forecast'):
            forecast.append('%s, %s: %s, high %s %s, low %s %s' % (
                x.getAttribute('day'), x.getAttribute('date'),
                x.getAttribute('text'),
                x.getAttribute('high'), temperature_units,
                x.getAttribute('low'), temperature_units))
        forecast.append('Full forecast from Yahoo! Weather: %s' % doc.getElementsByTagName('item')[0].getElementsByTagName('link')[0].firstChild.data)
        self.forecast = '\n'.join(forecast)

        location = doc.getElementsByTagName('yweather:location')[0]
        if location.getAttribute('region'):
            location = ', '.join([location.getAttribute('city'),
                                  location.getAttribute('region'),
                                  location.getAttribute('country')])
        else:
            location = ', '.join([location.getAttribute('city'),
                                  location.getAttribute('country')])

        self.info = """Weather for %s, from Yahoo! Weather <http://weather.yahoo.com>.
full forecast: <%s>
feed url: <%s>
%s is at: lat %s, long %s""" % (location,
                                doc.getElementsByTagName('item')[0].getElementsByTagName('link')[0].firstChild.data,
                                self.url,
                                location, doc.getElementsByTagName('geo:lat')[0].firstChild.data, doc.getElementsByTagName('geo:long')[0].firstChild.data)

        #self.update_time = 60*int(doc.getElementsByTagName('ttl')[0].firstChild.data) + time.time()
        self.update_time = random_periodic_update_time()


class WeatherNetwork:
    """Fetch weather from The Weather Network <http://www.theweathernetwork.com>
    """
    def __init__(self,opts):
        self.url = 'http://rss.theweathernetwork.com/weather/%s' % opts['location']

    commands = ['forecast', 'info']
    forecast_help = 'displays the current forecast'
    info_help = 'displays information on this weather feed'

    # FIXME:


class RosterStorage:
    """Class used to abstract out the roster storage.
    This class just uses pickle.
    """
    def read(self):
        filename = path.join(spooldir,'roster')
        try:
            fp = open(filename)
            if fp:
                rv = pickle.load(fp)
                fp.close()
                return rv
        except IOError, e:
            if e.errno != errno.ENOENT:
                raise
        return {}

    def save(self,roster):
        filename = path.join(spooldir,'roster')
        fp = open(filename,'w')
        if fp:
            pickle.dump(roster,fp)
            fp.close()

class WeatherBot:
    """Main weather bot class
    This class handles the bot's connection to the Jabber server, and processes
    messages from the server.
    """
    def __init__(self):
        self.rosterstorage = rosterstorage = RosterStorage()
        self.roster = roster = rosterstorage.read()
        rosterchanged = False
        for x in bots.iterkeys():
            if not roster.has_key(x):
                roster[x] = set()
                rosterchanged = True
        if rosterchanged:
            rosterstorage.save(roster)

        self.conn = conn = xmpp.client.Component(server, port)
        conn.connect()
        conn.auth(jid,password)

        # register handlers
        conn.RegisterDisconnectHandler(conn.reconnectAndReauth)
        conn.RegisterHandler('message',self.message_callback)
        conn.RegisterHandler('presence',self.subscribe_callback,typ='subscribe')
        conn.RegisterHandler('presence',self.unsubscribe_callback,typ='unsubscribe')
        conn.RegisterHandler('presence',self.probe_callback,typ='probe')

    def message_callback(self, conn, message):
        """Handle messages from users
        """
        to_user = xmpp.protocol.JID(jid=message.getTo())
        if not bots.has_key(to_user.getNode()):
            # sent to unknown user: ignore
            return
        # find the bot to send the reply from
        resource = to_user.getResource()
        if not resource:
            priority = -1
            for (res,(bot,pri)) in bots[to_user.getNode()].iteritems():
                if pri > priority:
                    resource = res
        else:
            if not bots[to_user.getNode()].has_key(resource):
                # sent to unknown resource: ignore
                return
        bot = bots[to_user.getNode()][resource][0]

        # process the command
        command = message.getBody().split(None,1)[0].strip()
        if command == 'help':
            commands = []
            for command in bot.commands:
                if hasattr(bot,'%s_help' % command):
                    commands.append('%s - %s' % (command, getattr(bot,'%s_help' % command)))
                else:
                    commands.append(command)
            replytxt = '\n'.join(commands)
        elif command not in bot.commands:
            replytxt = 'error: unknown command "%s"' % command
        elif hasattr(bot,'handle_%s' % command):
            return getattr(bot, 'handle_%s' % command)(conn, message)
        elif hasattr(bot,'get_%s' % command):
            replytxt = getattr(bot, 'get_%s' % command)(message)
        else:
            replytxt = getattr(bot, command)
        reply = message.buildReply(replytxt)
        reply.setType(message.getType())
        conn.send(reply)
        raise xmpp.NodeProcessed()

    def subscribe_callback(self, conn, presence):
        """Handle subscription requests
        """
        to_user = xmpp.protocol.JID(jid=presence.getTo())
        from_user = xmpp.protocol.JID(jid=presence.getFrom())
        if bots.has_key(to_user.getNode()):
            # valid user: subscribe
            # update the roster
            self.roster[to_user.getNode()].add(from_user.getStripped())
            self.rosterstorage.save(self.roster)
            # send subscribed stanza
            reply = xmpp.protocol.Presence(to=from_user.getStripped(),typ='subscribed',frm=to_user.getStripped())
            conn.send(reply)
            # send initial presence
            node = bots[to_user.getNode()]
            for (resource,(bot,priority)) in node.iteritems():
                reply = bot.presence
                reply.setPriority(priority)
                reply.setFrom("%s/%s" % (to_user.getStripped(),resource))
                reply.setTo(from_user.getStripped())
                conn.send(reply)
        else:
            # unknown user: send unsubscribe as error
            reply = xmpp.protocol.Presence(to=from_user.getStripped(),typ='unsubscribed',frm=to_user.getStripped())
            conn.send(reply)
        raise xmpp.NodeProcessed()

    def unsubscribe_callback(self, conn, presence):
        """Handle unsubscription requests
        """
        to_user = xmpp.protocol.JID(jid=presence.getTo())
        from_user = xmpp.protocol.JID(jid=presence.getFrom())
        if bots.has_key(to_user.getNode()):
            # update the roster
            self.roster[to_user.getNode()].discard(from_user.getStripped())
            self.rosterstorage.save(self.roster)
        raise xmpp.NodeProcessed()

    def probe_callback(self, conn, presence):
        """Handle presence probes
        """
        to_user = xmpp.protocol.JID(jid=presence.getTo())
        from_user = xmpp.protocol.JID(jid=presence.getFrom())
        if bots.has_key(to_user.getNode()) and \
           from_user.getStripped() in self.roster[to_user.getNode()]:
            node = bots[to_user.getNode()]
            for (resource,(bot,priority)) in node.iteritems():
                reply = bot.presence
                reply.setPriority(priority)
                reply.setFrom('%s/%s' % (to_user.getStripped(),resource))
                reply.setTo(from_user.getStripped())
                conn.send(reply)
        raise xmpp.NodeProcessed()

bots_updated_lock = threading.Lock()
bots_updated = set()

class WeatherUpdater(threading.Thread):
    """Update weather data periodically
    """
    def __init__(self):
        # load all the bot data
        for (node,x) in bots.iteritems():
            for (resource,y) in x.iteritems():
                y[0].refresh()
                bots_updated_lock.acquire()
                bots_updated.add((node,resource))
                bots_updated_lock.release()

        threading.Thread.__init__(self)
        self.setDaemon(True)

        self.active = True

    def run(self):
        while self.active:
            curtime = time.time()
            for (node,x) in bots.iteritems():
                for (resource,y) in x.iteritems():
                    bot = y[0]
                    if hasattr(bot,'refresh_test'):
                        if bot.refresh_test(curtime):
                            try:
                                bot.refresh()
                                bots_updated_lock.acquire()
                                bots_updated.add((node,resource))
                                bots_updated_lock.release()
                            except:
                                pass
                    else:
                        if bot.update_time < curtime:
                            try:
                                bot.refresh()
                                bots_updated_lock.acquire()
                                bots_updated.add((node,resource))
                                bots_updated_lock.release()
                            except:
                                pass
            time.sleep(20)

# various configuration variables
jid = ''
server = ''
port = 0
password = ''
spooldir = ''
bots = {}

if __name__ == "__main__":
    config = RawConfigParser()
    config.read(['/etc/weatherbot.cfg','weatherbot.cfg'])

    jid = config.get('DEFAULT','jid')
    server = config.get('DEFAULT','server')
    port = config.getint('DEFAULT','port')
    password = config.get('DEFAULT','password')
    spooldir = config.get('DEFAULT','spooldir')

    for section in config.sections():
        name, resource = section.split('/',1)
        if not bots.has_key(name):
            bots[name] = {}
        options = {}
        for (k,v) in config.items(section):
            options[k] = v
        bots[name][resource] = (globals()[config.get(section,'class')](options),
                                config.getint(section,'priority'))

    weatherbot = WeatherBot()
    updater = WeatherUpdater()
    updater.start()
    try:
        while True:
            weatherbot.conn.Process(10)
            bots_updated_lock.acquire()
            for (node,resource) in bots_updated:
                (bot,priority) = bots[node][resource]
                presence = bot.presence
                presence.setPriority(priority)
                presence.setFrom('%s@%s/%s' % (node,jid,resource))
                for user in weatherbot.roster[node]:
                    presence.setTo(user)
                    weatherbot.conn.send(presence)
            bots_updated.clear()
            bots_updated_lock.release()
    except:
        weatherbot.conn.UnregisterDisconnectHandler(weatherbot.conn.reconnectAndReauth)
        updater.active = False

        # send unavailable presence to all users
        presence = xmpp.protocol.Presence(typ='unavailable')
        for (node,x) in bots.iteritems():
            for resource in x.iterkeys():
                presence.setFrom('%s@%s/%s' % (node,jid,resource))
                for user in weatherbot.roster[node]:
                    presence.setTo(user)
                    weatherbot.conn.send(presence)

        # updater.join() ?

        weatherbot.conn.disconnect()
