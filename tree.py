#
# Kopirajto © 2022 Jean Michault
# Licenco «GPL-3.0-or-later»
#
# Ĉi tiu programo estas libera programaro; vi povas redistribui ĝin kaj/aŭ modifi
# ĝi laŭ la kondiĉoj de la Ĝenerala Publika Permesilo de GNU kiel eldonita de
# la Free Software Foundation; ĉu versio 3 de la Licenco, aŭ
# (laŭ via elekto) ajna posta versio.
#
# Ĉi tiu programo estas distribuata kun la espero, ke ĝi estos utila,
# sed SEN AJN GARANTIO; sen eĉ la implicita garantio de
# KOMERCEBLECO aŭ TAĜECO POR APARTA CELO. Vidu la
# GNU Ĝenerala Publika Permesilo por pliaj detaloj.
#
# Vi devus esti ricevinta kopion de la Ĝenerala Publika Permesilo de GNU
# kune kun ĉi tiu programo; se ne, skribu al 
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

from typing import Union

import sys
import re
import asyncio
from urllib.parse import unquote

# gedcomx biblioteko. Instalu kun `pip install gedcomx-v1`
import gedcomx

# local imports
from constants import (
    MAX_PERSONS,
    FACT_EVEN,
    FACT_TAGS,
    ORDINANCES_STATUS,
)
from gedcomx.dateformal import DateFormal

import gettext
_ = gettext.gettext

# ununura sesio uzata por ĉiuj «Tree»
_FsSeanco = None


class Tree(gedcomx.Gedcomx):
    """ gedcomx tree class
    """
    def __init__(self):
        gedcomx._utila.klaso_ini(self)
        self._fam = dict()
        self._places = dict()
        self._persons = dict()
        self._getsources = True
        self._sources = dict()
        self._notes = list()

    def add_persons(self, fids):
        """add individuals to the family tree
        :param fids: an iterable of fid
        """
        new_fids = [fid for fid in fids if fid and fid not in gedcomx.Person._indekso]
        while new_fids:
            if len(new_fids) ==1:
              data = _FsSeanco.get_jsonurl(
                "/platform/tree/persons/" + new_fids[0]
              )
            else:
              data = _FsSeanco.get_jsonurl(
                "/platform/tree/persons?pids=" + ",".join(new_fids[:MAX_PERSONS])
              )
            if data:
              gedcomx.maljsonigi(self,data)
            new_fids = new_fids[MAX_PERSONS:]
        for fid in fids :
          if fid in gedcomx.Person._indekso :
            self._persons[fid]=gedcomx.Person._indekso[fid]

    def add_parents(self, fids):
        """add parents relationships
        :param fids: a set of fids
        """
        rels = set()
        for fid in fids & self._persons.keys():
          for paro in self._persons[fid]._gepatroj :
            if paro.person1 : rels.add(paro.person1.resourceId)
            if paro.person2 : rels.add(paro.person2.resourceId)
          for cp in self._persons[fid]._gepatrojCP :
            if cp.parent1 : rels.add(cp.parent1.resourceId)
            if cp.parent2 : rels.add(cp.parent2.resourceId)
        rels.difference_update(fids)
        self.add_persons(rels)
        return set(filter(None, rels))

    def add_spouses(self, fids):
        """add spouse relationships
        :param fids: a set of fid
        """
        rels = set()
        for fid in fids & self._persons.keys():
          for paro in self._persons[fid]._paroj :
            rels |= {paro.person1.resourceId , paro.person2.resourceId }
        rels.difference_update(fids)
        self.add_persons(rels)
        return set(filter(None, rels))

    def add_children(self, fids):
        """add children relationships
        :param fids: a set of fid
        """
        rels = set()
        for fid in fids & self._persons.keys():
          for paro in self._persons[fid]._infanoj :
            rels |= {paro.person1.resourceId , paro.person2.resourceId }
        rels.difference_update(fids)
        self.add_persons(rels)
        return set(filter(None, rels))

    #def get_marriage_notes(self,ids):
        #"""retrieve marriage notes"""
        #if self.fid:
        #    notes = _FsSeanco.get_jsonurl(
        #        "/platform/tree/couple-relationships/%s/notes" % self.fid
        #    )
        #    if notes:

    #def add_marriage(self, fid):
        #"""retrieve and add marriage information
        #:param fid: the marriage fid
        #"""
        #if not self.fid:
        #    self.fid = fid
        #    url = "/platform/tree/couple-relationships/%s" % self.fid
        #    data = _FsSeanco.get_jsonurl(url)
    #def get_notes(self,id):
        #"""retrieve individual notes"""
        #notes = _FsSeanco.get_jsonurl("/platform/tree/persons/%s/notes" % self.id)
        #if notes:
    #def get_person_contributors(self,id):
        #"""retrieve contributors"""
        #temp = set()
        #url = "/platform/tree/persons/%s/changes" % self.id
        #data = _FsSeanco.get_jsonurl(url, {"Accept": "application/x-gedcomx-atom+json"})
        #if data:
    #def
        #    # FARINDAĴO : portrait
        #    #if "links" in data:
        #    #    req = _FsSeanco.get_jsonurl(
        #    #        "/platform/tree/persons/%s/portrait" % self.id
        #    #        , {"Accept": "image/*"}
        #    #    )
        #    #    if req and req.text:
    #def
        #    if "evidence" in data:
        #        url = "/platform/tree/persons/%s/memories" % self.id
        #        memorie = _FsSeanco.get_jsonurl(url)
        #        if memorie and "sourceDescriptions" in memorie:
    #def get_person_contributors(self):
        #"""retrieve contributors"""
        #temp = set()
        #url = "/platform/tree/persons/%s/changes" % self.id
        #data = _FsSeanco.get_jsonurl(url, {"Accept": "application/x-gedcomx-atom+json"})
    #def add_marriage(self, fid):
        #"""retrieve and add marriage information
        #:param fid: the marriage fid
        #"""
        #if not self.fid:
        #    self.fid = fid
        #    url = "/platform/tree/couple-relationships/%s" % self.fid
        #    data = _FsSeanco.get_jsonurl(url)
        #    if data:
