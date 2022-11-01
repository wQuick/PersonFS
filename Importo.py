#
# interfaco por familysearch
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

"""
" «FamilySearch» importo.
"""


from gramps.gen.db import DbTxn
from gramps.gen.config import config
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.lib import Attribute, ChildRef, Date, Event, EventRef, EventType, EventRoleType, Family, Name, NameType, Person, Place, PlaceName, PlaceRef, PlaceType
from gramps.gen.plug.menu import StringOption, PersonOption, BooleanOption, NumberOption, FilterOption, MediaOption
from gramps.gui.dialog import WarningDialog, QuestionDialog2
from gramps.gui.plug import MenuToolOptions, PluginWindows
from gramps.plugins.lib.libgedcom import PERSONALCONSTANTEVENTS, FAMILYCONSTANTEVENTS, GED_TO_GRAMPS_EVENT, TOKENS


from PersonFS import PersonFS
from getmyancestors.classes.tree import Tree, Name as fsName, Indi, Fact
from getmyancestors.classes.constants import FACT_TAGS

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

# tutmondaj variabloj
vorteco = 0

class FSImportoOpcionoj(MenuToolOptions):
  """
  " 
  """
  def __init__(self, name, person_id=None, dbstate=None):
    """
    " 
    """
    if vorteco >= 3:
      print(_("Kromprogramoj"))
    MenuToolOptions.__init__(self, name, person_id, dbstate)

  def add_menu_options(self, menu):
    """
    " 
    """
    category_name = _("FamilySearch Importo Opcionoj")
    self.__FS_ID = StringOption(_("FamilySearch ID"), 'XXXX-XXX')
    self.__FS_ID.set_help(_("identiga numero por esti prenita de FamilySearch retejo"))
    menu.add_option(category_name, "FS_ID", self.__FS_ID)
    self.__gui_asc = NumberOption(_("Nombro ascentontaj"), 0, 0, 99)
    self.__gui_asc.set_help(_("Nombro de generacioj por supreniri"))
    menu.add_option(category_name, "gui_asc", self.__gui_asc)
    self.__gui_desc = NumberOption(_("Nombro descendontaj"), 0, 0, 99)
    self.__gui_desc.set_help(_("Nombro de generacioj descendontaj"))
    menu.add_option(category_name, "gui_desc", self.__gui_desc)
    self.__gui_edz = BooleanOption(_("Aldonu geedzoj"), False)
    self.__gui_edz.set_help(_("Aldonu informojn pri geedzoj kaj paro"))
    menu.add_option(category_name, "gui_edz", self.__gui_edz)
    self.__gui_vort = NumberOption(_("Vorteco"), 0, 0, 3)
    self.__gui_vort.set_help(_("Vorteca nivelo de 0 (minimuma) ĝis 3 (tre vorta)"))
    menu.add_option(category_name, "gui_vort", self.__gui_vort)

    if vorteco >= 3:
      print(_("Menuo Aldonita"))

class FSImporto(PluginWindows.ToolManagedWindowBatch):
  """
  " 
  """
  fs_TreeImp = None
  fs_gr = None
  def __init__(self, dbstate, user, options_class, name, callback):
    """
    " 
    """
    PluginWindows.ToolManagedWindowBatch.__init__(self, dbstate, user, options_class, name, callback)

  def get_title(self):
    """
    " 
    """
    print(_("Plugin get_title"))
    return _("FamilySearch Import Tool")  # tool window title

  def initial_frame(self):
    """
    " 
    """
    print(_("Plugin initial_frame"))
    return _("FamilySearch Importo Opcionoj")  # tab title

  def run(self):
    """
    " 
    """
    print(_("Plugin run"))
    self.__get_menu_options()
    print("import ID "+self.FS_ID)
    self.fs_gr = dict()
    # sercxi ĉi tiun numeron en «gramps».
    for person_handle in self.dbstate.db.get_person_handles() :
      person = self.dbstate.db.get_person_from_handle(person_handle)
      for attr in person.get_attribute_list():
        if attr.get_type() == '_FSFTID' and attr.get_value() ==self.FS_ID :
          d = QuestionDialog2(_('«FamilySearch» ekzistanta ID')
                 ,_('«FamilySearch» ID uzata per %s.\n   Se vi daŭrigos, kreiĝos nur neekzistantaj personoj.\n\n      Ĉu vi volas daŭrigi?') % {person.gramps_id}
                 ,_('daŭrigi')
                 ,_('Cancel') )
          if not d.run():
            return
        if attr.get_type() == '_FSFTID':
          self.fs_gr[attr.get_value()] = person_handle
          break
    if not self.fs_TreeImp :
      self.fs_TreeImp = Tree(PersonFS.fs_Session)
    else:
      self.fs_TreeImp.__init__(PersonFS.fs_Session)
    # Legi la personojn en «FamilySearch».
    if self.FS_ID:
      self.fs_TreeImp.add_indis([self.FS_ID])
    else : return
    # ascendante
    todo = set(self.fs_TreeImp.indi.keys())
    done = set()
    for i in range(self.asc):
      if not todo:
        break
      done |= todo
      print( _("Downloading %s. of generations of ancestors...") % (i + 1))
      todo = self.fs_TreeImp.add_parents(todo) - done
    # descendante
    todo = set(self.fs_TreeImp.indi.keys())
    done = set()
    for i in range(self.desc):
      if not todo:
        break
      done |= todo
      print( _("Downloading %s. of generations of descendants...") % (i + 1))
      todo = self.fs_TreeImp.add_children(todo) - done
    # edzoj
    if self.edz :
      print(_("Downloading spouses and marriage information..."))
      todo = set(self.fs_TreeImp.indi.keys())
      self.fs_TreeImp.add_spouses(todo)

    with DbTxn("FamilySearch import", self.dbstate.db) as txn:
      self.txn = txn
      # importi lokoj
      for id,pl in self.fs_TreeImp.places.items() :
        print("place, id="+id)
        self.aldLoko(id,pl)
      # importi personoj
      for id in self.fs_TreeImp.indi.keys() :
        self.aldPersono(id)
      # importi familioj
      for fsFam in self.fs_TreeImp.fam.values() :
        self.aldFamilio(fsFam)
  
      # FARINDAĴOJ : notoj, fontoj

    print("import fini.")

  def akiriLoko(self, nomo, parent):
    # sercxi por loko kun cî nomo
    for handle in self.db.get_place_handles():
      place = self.db.get_place_from_handle(handle)
      if place.name.value == nomo :
        return place
      for name in place.get_alternative_names():
        if name.value == nomo :
          return place
    return None

  def kreiLoko(self, nomo, parent):
    place = self.akiriLoko(nomo, parent)
    if place:
      return place
    place = Place()
    place_name = PlaceName()
    place_name.set_value( nomo )
    place.set_name(place_name)
    place.set_title(nomo)
    place_type = None
    if not parent:
      place_type = PlaceType(1)
    else:
      if parent.place_type == PlaceType(1):
        place_type = PlaceType(9)
      elif parent.place_type == PlaceType(9):
        place_type = PlaceType(10)
      elif parent.place_type == PlaceType(10):
        place_type = PlaceType(14)
      elif parent.place_type == PlaceType(14):
        place_type = PlaceType(20)
      placeref = PlaceRef()
      placeref.ref = parent.handle
      place.add_placeref(placeref)
    place.set_type(place_type)
    self.dbstate.db.add_place(place, self.txn)
    return place



  def aldLoko(self, id, pl):
    nomo = pl[2][0]["value"]
    pl[2][0]["handle"] = None
    # sercxi por loko kun cî nomo
    grLoko = self.akiriLoko(nomo, None)
    if grLoko:
      pl[2][0]["handle"] = grLoko.handle
      return
    
    partoj = nomo.split(', ')
    if len(partoj) <1:
      return

    # FARINDAĴOJ : administri naciajn apartaĵojn
    lando = partoj.pop(len(partoj)-1)
    grLando = self.kreiLoko(lando, None)
    if grLando:
      pl[2][0]["handle"] = grLando.handle
    if len(partoj) <1:
      return

    regiono = partoj.pop(len(partoj)-1)
    grRegiono = self.kreiLoko(regiono, grLando)
    if grRegiono:
      pl[2][0]["handle"] = grRegiono.handle
    if len(partoj) <1:
      return

    fako = partoj.pop(len(partoj)-1)
    grFako = self.kreiLoko(fako, grRegiono)
    if grFako:
      pl[2][0]["handle"] = grFako.handle
    if len(partoj) <1:
      return

    municipo = partoj.pop(len(partoj)-1)
    grMunicipo = self.kreiLoko(municipo, grFako)
    if grMunicipo:
      pl[2][0]["handle"] = grMunicipo.handle
    if len(partoj) <1:
      pn = PlaceName()
      pn.set_value(nomo)
      grMunicipo.add_alternative_name(pn)
      self.dbstate.db.commit_place(grMunicipo, self.txn)
      return

    # FARINDAĴOJ
    print("neatendita enhavo en nomloko!")
    lokloko = ", ".join(partoj)
    grLoko = self.kreiLoko(lokloko, grMunicipo)
    pl[2][0]["handle"] = grLoko.handle
    pn = PlaceName()
    pn.set_value(nomo)
    grLoko.add_alternative_name(pn)
    self.dbstate.db.commit_place(grLoko, self.txn)


  def aldFamilio(self,fsFam):
    familio = None
    grPatroHandle = self.fs_gr.get(fsFam.husb_fid)
    grPatrinoHandle = self.fs_gr.get(fsFam.wife_fid) 
    if grPatroHandle :
      grPatro = self.dbstate.db.get_person_from_handle(grPatroHandle)
      if grPatrinoHandle :
        grPatrino = self.dbstate.db.get_person_from_handle(grPatrinoHandle)
      else :
        grPatrino = None
      for family_handle in grPatro.get_family_handle_list():
        if not family_handle: continue
        f = self.dbstate.db.get_family_from_handle(family_handle)
        if f.get_mother_handle() == grPatrinoHandle :
          familio = f
          break
    elif grPatrinoHandle :
      grPatro = None
      grPatrino = self.dbstate.db.get_person_from_handle(grPatrinoHandle)
      for family_handle in grPatrino.get_family_handle_list():
        if not family_handle: continue
        f = self.dbstate.db.get_family_from_handle(family_handle)
        if f.get_father_handle() == None :
          familio = f
          break
    else:
      print(_('sengepatra familio ???'))
      return
    if not familio :
      familio = Family()
      familio.set_father_handle(grPatroHandle)
      familio.set_mother_handle(grPatrinoHandle)
      self.dbstate.db.add_family(familio, self.txn)
      self.dbstate.db.commit_family(familio, self.txn)
      if grPatro:
        grPatro.add_family_handle(familio.get_handle())
        self.dbstate.db.commit_person(grPatro, self.txn)
      if grPatrino:
        grPatrino.add_family_handle(familio.get_handle())
        self.dbstate.db.commit_person(grPatrino, self.txn)
    # FARINDAĴO : edziĝo
    for c in fsFam.chil_fid:
      infanoHandle = self.fs_gr.get(c)
      found = False
      for cr in familio.get_child_ref_list() :
        if cr.get_reference_handle() == infanoHandle:
          found = True
          break
      if not found :
        childref = ChildRef()
        childref.set_reference_handle(infanoHandle)
        familio.add_child_ref(childref)
        self.dbstate.db.commit_family(familio, self.txn)
        infano = self.dbstate.db.get_person_from_handle(infanoHandle)
        infano.add_parent_family_handle(familio.get_handle())
        self.dbstate.db.commit_person(infano, self.txn)
    return

  def aldPersono(self,fsid):
    if self.fs_gr.get(fsid) :
      return
    fsPerso = self.fs_TreeImp.indi.get(fsid)
    if not fsPerso :
      print(_("ID ne trovita."))
      return
    grPerson = Person()
    nomo = Name()
    nomo.set_type(NameType(NameType.BIRTH))
    nomo.set_first_name(fsPerso.name.given)
    s = nomo.get_primary_surname()
    s.set_surname(fsPerso.name.surname)
    grPerson.set_primary_name(nomo)
    if fsPerso.gender == "M" :
      grPerson.set_gender(Person.MALE)
    elif fsPerso.gender == "F" :
      grPerson.set_gender(Person.FEMALE)
    attr = Attribute()
    attr.set_type('_FSFTID')
    attr.set_value(fsid)
    grPerson.add_attribute(attr)

    self.dbstate.db.add_person(grPerson,self.txn)
    self.dbstate.db.commit_person(grPerson,self.txn)
    self.fs_gr[fsid] = grPerson.handle

    # FARINDAĴO : faktoj
    for fsFakto in fsPerso.facts:
      gedTag = FACT_TAGS.get(fsFakto.type) or fsFakto.type
      if not gedTag :
        continue
      evtType = GED_TO_GRAMPS_EVENT.get(gedTag) or gedTag
      fsFaktoLoko = fsFakto.place or ''
      print("fsFaktoLoko="+fsFaktoLoko)
      print(self.fs_TreeImp.places)
      #pl = self.fs_TreeImp.places.get(fsFakto.placeid)
      #print(pl)
      #if pl :
      if fsFakto.map:
        grLokoHandle = fsFakto.map[2][0]["handle"]
      else: grLokoHandle = None
      print(grLokoHandle)
      fsFaktoPriskribo = fsFakto.value or ''
      fsFaktoDato = fsFakto.date or ''
      if fsFakto.date:
        grDate = Date()
        if fsFakto.date[0] == 'A' :
          grDate.set_modifier(Date.MOD_ABOUT)
        elif fsFakto.date[0] == '/' :
          grDate.set_modifier(Date.MOD_BEFORE)
        posSigno = fsFakto.date.find('+')
        posMinus = fsFakto.date.find('-')
        if posMinus >= 0 and (posSigno <0 or posSigno > posMinus) :
          posSigno = posMinus
        if len(fsFakto.date) >= posSigno+5 :
          jaro = fsFakto.date[posSigno+0:posSigno+5]
        else: jaro='0'
        if len(fsFakto.date) >= posSigno+8 :
          monato = fsFakto.date[posSigno+6:posSigno+8]
        else: monato='0'
        if len(fsFakto.date) >= posSigno+11 :
          tago = fsFakto.date[posSigno+9:posSigno+11]
        else: tago='0'
        # FARINDAĴO : kompleksaj datoj
        grDate.set_yr_mon_day(int(jaro), int(monato), int(tago))
      else : grDate = None

      event = Event()
      event.set_type( evtType )
      if grLokoHandle:
        event.set_place_handle( grLokoHandle )
      if grDate :
        event.set_date_object( grDate )
      event.set_description(fsFaktoPriskribo)
      #tag = db.get_tag_from_name( xxx )
      #event.add_tag(tag.handle)
      self.dbstate.db.add_event(event, self.txn)
      eventref = EventRef()
      eventref.set_role(EventRoleType.PRIMARY)
      eventref.set_reference_handle(event.get_handle())
      self.dbstate.db.commit_event(event, self.txn)
      grPerson.add_event_ref(eventref)
    self.dbstate.db.commit_person(grPerson,self.txn)

  def __get_menu_options(self):
    print(_("Plugin __get_menu_options"))
    menu = self.options.menu
    self.FS_ID = self.options.menu.get_option_by_name('FS_ID').get_value()
    self.asc = self.options.menu.get_option_by_name('gui_asc').get_value()
    self.desc = self.options.menu.get_option_by_name('gui_desc').get_value()
    self.edz = self.options.menu.get_option_by_name('gui_edz').get_value()

