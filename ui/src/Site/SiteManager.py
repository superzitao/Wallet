import atexit
import json
import logging
import re
import time

import gevent
from Config import config
from Plugin import PluginManager
from util import helper


@PluginManager.acceptPlugins
class SiteManager(object):
    def __init__(self):
        self.log = logging.getLogger("SiteManager")
        self.log.debug("SiteManager created.")
        self.sites = None
        self.loaded = False
        gevent.spawn(self.saveTimer)
        atexit.register(self.save)

    # Load all sites from data/sites.json
    def load(self, cleanup=True):
        self.loaded = False
        if self.sites is None:
            self.sites = {}
        added = 0

        if added:
            pass
            # self.log.debug("SiteManager added %s sites" % added)
        self.loaded = True

    def save(self):
        if not self.sites:
            # self.log.debug("Save skipped: No sites found")
            return
        if not self.loaded:
            # self.log.debug("Save skipped: Not loaded")
            return
        s = time.time()
        data = {}
        # Generate data file
        for address, site in self.list().iteritems():
            site.settings["size"] = site.content_manager.getTotalSize()  # Update site size
            data[address] = site.settings
            data[address]["cache"] = {}
            # data[address]["cache"]["bad_files"] = site.bad_files
            # data[address]["cache"]["hashfield"] = site.content_manager.hashfield.tostring().encode("base64")

        if data:
            helper.atomicWrite("%s/sites.json" % config.data_dir, json.dumps(data, indent=2, sort_keys=True))
        else:
            pass
            # self.log.debug("Save error: No data")
        # Remove cache from site settings
        for address, site in self.list().iteritems():
            site.settings["cache"] = {}

        # self.log.debug("Saved sites in %.2fs" % (time.time() - s))

    def saveTimer(self):
        while 1:
            time.sleep(60 * 10)
            self.save()

    # Checks if its a valid address
    def isAddress(self, address):
        return re.match("^[A-Za-z0-9]{26,35}$", address)

    def isDomain(self, address):
        return False

    # Return: Site object or None if not found
    def get(self, address):
        if self.sites is None:  # Not loaded yet
            # self.log.debug("Getting new site: %s)..." % address)
            self.load()
        return self.sites.get(address)

    # Return or create site and start download site files
    def need(self, address, all_file=True):
        from Site import Site
        site = self.get(address)
        if not site:  # Site not exist yet
            # Try to find site with differect case
            for recover_address, recover_site in self.sites.items():
                if recover_address.lower() == address.lower():
                    return recover_site

            if not self.isAddress(address):
                return False  # Not address: %s % address
            # self.log.debug("Added new site: %s" % address)
            site = Site(address)
            self.sites[address] = site
            if not site.settings["serving"]:  # Maybe it was deleted before
                site.settings["serving"] = True
            site.saveSettings()
            if all_file:  # Also download user files on first sync
                site.download(check_size=True, blind_includes=True)

        return site

    def delete(self, address):
        # self.log.debug("SiteManager deleted site: %s" % address)
        del(self.sites[address])
        # Delete from sites.json
        self.save()

    # Lazy load sites
    def list(self):
        if self.sites is None:  # Not loaded yet
            # self.log.debug("Sites not loaded yet...")
            self.load()
        return self.sites


site_manager = SiteManager()  # Singletone

peer_blacklist = [("127.0.0.1", config.fileserver_port)]  # Dont add this peers