#
# Gramplet - fs (interfaco por familysearch)
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

import email.utils
import time
from urllib.parse import unquote
from utila import get_fsftid, get_grevent, get_fsfact, grdato_al_formal
from gramps.gen.lib.attrtype import AttributeType

from gramps.gen.plug.menu import FilterOption, TextOption, NumberOption, BooleanOption
from gramps.gen.db import DbTxn
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.display.place import displayer as _pd
from gramps.gen.filters import CustomFilters, GenericFilterFactory, rules
from gramps.gen.lib import Date, EventRoleType, EventType, Person, Attribute

from gramps.gui.dialog import OkDialog, WarningDialog
from gramps.gui.plug import MenuToolOptions, PluginWindows
from gramps.gui.utils import ProgressMeter

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

import gedcomx

import PersonFS
import fs_db
import tree
import utila
from constants import GEDCOMX_GRAMPS_FAKTOJ,GRAMPS_GEDCOMX_FAKTOJ

#from objbrowser import browse ;browse(locals())
#import pdb; pdb.set_trace()

class FSAutoMatchOpcionoj(MenuToolOptions):

  def __init__(self, name, person_id=None, dbstate=None):
    #print("KO.init")
    self.db = dbstate.get_database()
    MenuToolOptions.__init__(self, name, person_id, dbstate)

  def add_menu_options(self, menu):
    #print("KO.amo")
    self.__general_options(menu)

  def __general_options(self, menu):
    #print("KO.go")
    category_name = _("FamilySearch AutoMatch Opcionoj")
    self.__gui_tagoj = NumberOption(_("Nombro tagoj"), 0, 0, 99)
    self.__gui_tagsc = NumberOption(_("Score"), 21, 15, 99)
    self.__gui_tagoj.set_help(_("Nombro da tagoj inter du komparoj"))
    self.__gui_tagsc.set_help(_("Minimum score number for automatch"))
    menu.add_option(category_name, "gui_tagoj", self.__gui_tagoj)
    menu.add_option(category_name, "gui_tagsc", self.__gui_tagsc)

    self.__gui_deviga = BooleanOption(_("Devigi komparo"), True) 
    self.__gui_deviga.set_help(_("Kompari sendepende de la nombro da tagoj."))
    menu.add_option(category_name, "gui_deviga", self.__gui_deviga)

    all_persons = rules.person.Everyone([])
    self.__gui_filter_name = FilterOption(_trans.gettext("Person Filter"), 0)
    menu.add_option(category_name,'Person', self.__gui_filter_name)
    # custom filter:
    filter_list = CustomFilters.get_filters('Person')
    # generic filter:
    GenericFilter = GenericFilterFactory('Person')
    all_filter = GenericFilter()
    all_filter.set_name(_trans.gettext("All %s") % (_trans.gettext("Persons")))
    all_filter.add_rule(all_persons)
    # only add the generic filter if it isn't already in the menu
    all_filter_in_list = False
    for fltr in filter_list:
        if fltr.get_name() == all_filter.get_name():
            all_filter_in_list = True
    if not all_filter_in_list:
        filter_list.insert(0, all_filter)
    self.__gui_filter_name.set_filters(filter_list)

class FSAutoMatch(PluginWindows.ToolManagedWindowBatch):

  def get_title(self):
    #print("K.title")
    return _("FamilySearch AutoMatch")

  def initial_frame(self):
    #print("K.options")
    return _trans.gettext("Options")
  def run(self):

    def get_fsftidscore(grObj):
      if not grObj:
        return ''
      for attr in grObj.get_attribute_list():
        if attr.get_type() == '_FSFTID_SCORE':
          return attr.get_value()
      return ''

    #print("K.run")
    if not PersonFS.PersonFS.aki_sesio(self):
      WarningDialog(_('Ne konektita al FamilySearch'))
      return
    progress = ProgressMeter(_("FamilySearch : AutoMatch"), _trans.gettext('Starting'),
                   can_cancel=True, parent=self.uistate.window)
    self.uistate.set_busy_cursor(True)
    self.dbstate.db.disable_signals()
    if not PersonFS.PersonFS.fs_Tree:
      PersonFS.PersonFS.fs_Tree = tree.Tree()
      PersonFS.PersonFS.fs_Tree._getsources = False
    self.db = self.dbstate.get_database()
    # krei datumbazan tabelon
    fs_db.create_schema(self.db)
    fs_db.create_tags(self.dbstate.db)
    # krei la ordigitan liston de personoj por procesi
    filter_ = self.options.menu.get_option_by_name('Person').get_filter()
    tagoj = self.options.menu.get_option_by_name('gui_tagoj').get_value()
    devigi = self.options.menu.get_option_by_name('gui_deviga').get_value()
    tagsc = self.options.menu.get_option_by_name('gui_tagsc').get_value()
    maks_dato = int(time.time()) - tagoj*24*3600
    self.plist = set(filter_.apply(self.db, self.db.iter_person_handles()))
    pOrdList = list()
    progress.set_pass(_('Konstruante la ordigitan liston (1/2)'), len(self.plist))
    print("liste filtrée : "+str(len(self.plist)))
    for handle in self.plist:
      if progress.get_cancelled() :
        self.uistate.set_busy_cursor(False)
        progress.close()
        self.dbstate.db.enable_signals()
        self.dbstate.db.request_rebuild()
        return
      progress.step()
      person = self.db.get_person_from_handle(handle)
      fsid = utila.get_fsftid(person)
      fsidscore = get_fsftidscore(person)
      if (fsid != '') and (fsidscore != ''):
        continue
      self.db.dbapi.execute("select stat_dato from personfs_stato where p_handle=?",[handle])
      datumoj = self.db.dbapi.fetchone()
      if datumoj and datumoj[0] :
        if devigi or datumoj[0] < maks_dato :
          pOrdList.append([datumoj[0],handle,fsid])
      else:
        pOrdList.append([0,handle,fsid])
    def akiUnua(ero):
      return ero[0]

    pOrdList.sort(key=akiUnua)
    # procesi
    progress.set_pass(_('Procesante la liston (2/2)'), len(pOrdList))
    print("liste triée : "+str(len(pOrdList)))
    kop_etik = PersonFS.PersonFS.fs_etikedado
    PersonFS.PersonFS.fs_etikedado = True
    
    import asyncio
    def ligi_gr_fs_score(db, grObjekto, fsidscore):
      attr = None
      if db.transaction:
        intr = True
        txn = db.transaction
      else:
        intr = False
        txn = DbTxn(_("FamilySearch etikedoj"), db)
      for attr in grObjekto.get_attribute_list():
        if attr.type.value == '_FSFTID_SCORE':
          attr.set_value(fsidscore)
          break
      if not attr or attr.type.value != '_FSFTID_SCORE':
        attr = Attribute()
        attr.set_type((AttributeType.CUSTOM, '_FSFTID_SCORE'))
        attr.set_value(fsidscore)
        grObjekto.add_attribute(attr)
      match grObjekto.__class__.__name__:
        case 'Person':
          db.commit_person(grObjekto, txn)
        case 'Event':
          db.commit_event(grObjekto, txn)
        case _:
          print("utila.ligi_gr_fs_score : klaso ne trakta : " + grObjekto.__class__.__name__)
      if not intr:
        db.transaction_commit(txn)
    def DataRes(person, datumoj):
      for entry in datumoj["entries"]:
        print (entry.get("id")+ ";  score = "+str(entry.get("score")))
        fsid = entry.get("id")
        fsScore = entry.get("score")
        ligi_gr_fs_score(self.dbstate.db, person, str(fsScore))
        if fsScore>=tagsc:
           #OkDialog(_('Achei Maior que: ' + str(fsScore) ))
           #utila.ligi_gr_fs(self.dbstate.db, person, fsid)
           print(entry.get("id") + ";  score = " + str(entry.get("score")))
      return
    def match_paro_p2(paro):
      person = self.db.get_person_from_handle(paro[1])

      #print("traitement "+person.gramps_id)

      pe_surname = person.primary_name.get_surname()
      pe_givename = person.primary_name.first_name

      pe_sex = ''
      if person.get_gender() == Person.MALE:
        pe_sex = 'Male'
      elif person.get_gender() == Person.FEMALE:
        pe_sex = 'Female'

      pe_birth = ''
      grBirth = get_grevent(self.dbstate.db, person, EventType(EventType.BIRTH))
      if grBirth == None or grBirth.date == None or grBirth.date.is_empty():
        grBirth = get_grevent(self.dbstate.db, person, EventType(EventType.CHRISTEN))
      if grBirth == None or grBirth.date == None or grBirth.date.is_empty():
        grBirth = get_grevent(self.dbstate.db, person, EventType(EventType.ADULT_CHRISTEN))
      if grBirth == None or grBirth.date == None or grBirth.date.is_empty():
        grBirth = get_grevent(self.dbstate.db, person, EventType(EventType.BAPTISM))
      if grBirth and grBirth.date and not grBirth.date.is_empty():
        naskoDato = grdato_al_formal(grBirth.date)
        if len(naskoDato) > 0 and naskoDato[0] == 'A': naskoDato = naskoDato[1:]
        if len(naskoDato) > 0 and naskoDato[0] == '/': naskoDato = naskoDato[1:]
        posOblikvo = naskoDato.find('/')
        if posOblikvo > 1: naskoDato = naskoDato[:posOblikvo]
        pe_birth = naskoDato

      pe_death = ''
      grDeath = get_grevent(self.dbstate.db, person, EventType(EventType.DEATH))
      if grDeath == None or grDeath.date == None or grDeath.date.is_empty():
        grDeath = get_grevent(self.dbstate.db, person, EventType(EventType.BURIAL))
      if grDeath == None or grDeath.date == None or grDeath.date.is_empty():
        grDeath = get_grevent(self.dbstate.db, person, EventType(EventType.CREMATION))
      if grDeath and grDeath.date and not grDeath.date.is_empty():
        mortoDato = grdato_al_formal(grDeath.date)
        if len(mortoDato) > 0 and mortoDato[0] == 'A': mortoDato = mortoDato[1:]
        if len(mortoDato) > 0 and mortoDato[0] == '/': mortoDato = mortoDato[1:]
        posOblikvo = mortoDato.find('/')
        if posOblikvo > 1: mortoDato = mortoDato[:posOblikvo]
        pe_death= mortoDato

      pe_birth_place=''
      if grBirth and grBirth.place and grBirth.place != None:
        place = self.dbstate.db.get_place_from_handle(grBirth.place)
        pe_birth_place = place.name.value

      # Get father and mother name
      family_handle = None
      father = None
      father_handle = None
      mother = None
      mother_handle = None

      pe_mother_givename = ''
      pe_mother_surname = ''
      pe_father_givename = ''
      pe_father_surname = ''
      pe_spose_givename = ''
      pe_spose_surname = ''

      family_handle = person.get_main_parents_family_handle()
      if family_handle:
        family = self.dbstate.db.get_family_from_handle(family_handle)
        mother_handle = family.get_mother_handle()
        father_handle = family.get_father_handle()
        if mother_handle:
          mother = self.dbstate.db.get_person_from_handle(mother_handle)
          pe_mother_surname = mother.primary_name.get_surname()
          pe_mother_givename = mother.primary_name.first_name
        if father_handle:
          father = self.dbstate.db.get_person_from_handle(father_handle)
          pe_father_surname = father.primary_name.get_surname()
          pe_father_givename = father.primary_name.first_name

      # Get Spose Name
      for family_handle in person.get_family_handle_list():
        pe_spose_givename = ''
        pe_spose_surname = ''
        family = self.dbstate.db.get_family_from_handle(family_handle)
        if family:
          edzo_handle = family.mother_handle
          if edzo_handle == person.handle:
            edzo_handle = family.father_handle
          if edzo_handle:
            edzo = self.dbstate.db.get_person_from_handle(edzo_handle)
            edzo_name = edzo.primary_name
            pe_spose_surname = edzo.primary_name.get_surname()
            pe_spose_givename = edzo.primary_name.first_name
            break

      # find familysearch
      mendo = "/platform/tree/search?"

      if pe_surname:         mendo = mendo + "q.surname=%s&" % pe_surname
      if pe_givename:        mendo = mendo + "q.givenName=%s&" % pe_givename
      if pe_sex:             mendo = mendo + "q.sex=%s&" % pe_sex
      if pe_birth:           mendo = mendo + "q.birthLikeDate=%s&" % pe_birth
      if pe_death:           mendo = mendo + "q.deathLikeDate=%s&" % pe_death
      if pe_birth_place:     mendo = mendo + "q.anyPlace=%s&" % pe_birth_place

      if pe_mother_givename: mendo = mendo + "q.motherGivenName=%s&" % pe_mother_givename
      if pe_mother_surname:  mendo = mendo + "q.motherSurname=%s&" % pe_mother_surname

      if pe_father_givename: mendo = mendo + "q.fatherGivenName=%s&" % pe_father_givename
      if pe_father_surname:  mendo = mendo + "q.fatherSurname=%s&" % pe_father_surname

      if pe_spose_givename:  mendo = mendo + "q.spouseGivenName=%s&" % pe_spose_givename
      if pe_spose_surname:   mendo = mendo + "q.spouseSurname=%s&" % pe_spose_surname

      mendo = mendo + "offset=0&count=1"

      #print(mendo)
      datumoj = tree._FsSeanco.get_jsonurl( mendo, {"Accept": "application/x-gedcomx-atom+json"} )
      #time.sleep(0.5)
      if not datumoj:
        return

      #tot = datumoj["results"]
      #print ("n. results = "+str(tot))

      DataRes(person, datumoj)
    
    for paro in pOrdList:
      if progress.get_cancelled() :
        self.uistate.set_busy_cursor(False)
        progress.close()
        self.dbstate.db.enable_signals()
        self.dbstate.db.request_rebuild()
        PersonFS.PersonFS.fs_etikedado = kop_etik
        return

      progress.step()

      try:
        match_paro_p2(paro)
      except Exception as e:
        print("WARNING: exception from %s, error: %s" % (url, e))

    PersonFS.PersonFS.fs_etikedado = kop_etik

    self.uistate.set_busy_cursor(False)
    progress.close()
    self.dbstate.db.enable_signals()
    self.dbstate.db.request_rebuild()
