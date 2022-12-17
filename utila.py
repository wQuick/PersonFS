from gramps.gen.db import DbTxn
from gramps.gen.lib import Attribute, EventRoleType, Date
from gramps.gen.lib.date import gregorian

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


def grdato_al_formal( dato) :
  """
  " konvertas gramps-daton al «formal» dato
  "   «formal» dato : <https://github.com/FamilySearch/gedcomx/blob/master/specifications/date-format-specification.md>
  """
  res=''
  gdato = gregorian(dato)
  if gdato.modifier == Date.MOD_ABOUT :
    res = 'A'
  elif gdato.modifier == Date.MOD_BEFORE:
    res = '/'
  if gdato.dateval[Date._POS_YR] < 0 :
    res = res + '-'
  else :
    res = res + '+'
  if gdato.dateval[Date._POS_DAY] > 0 :
    val = "%04d-%02d-%02d" % (
                gdato.dateval[Date._POS_YR], gdato.dateval[Date._POS_MON],
                gdato.dateval[Date._POS_DAY])
  elif gdato.dateval[Date._POS_MON] > 0 :
    val = "%04d-%02d" % (
                gdato.dateval[Date._POS_YR], gdato.dateval[Date._POS_MON])
  elif gdato.dateval[Date._POS_YR] > 0 :
    val = "%04d" % ( gdato.dateval[Date._POS_YR] )
  else :
    res = gdato.text
    val=''
  res = res+val
  if gdato.modifier == Date.MOD_AFTER:
    res = res + '/'
  # FARINDAĴOJ : range ?  estimate ? calculate ? heure ?
  
  return res

def getfsid(grPersono) :
  if not grPersono :
    return ''
  for attr in grPersono.get_attribute_list():
    if attr.get_type() == '_FSFTID':
      return attr.get_value()
  return ''

def get_fsfact(person, fact_tipo):
  """
  " Liveras la unuan familysearch fakton de la donita tipo.
  """
  for fact in person.facts :
    if fact.type == fact_tipo :
      return fact
  return None

def get_grevent(db, person, event_type):
  """
  " Liveras la unuan gramps eventon de la donita tipo.
  """
  if not person:
    return None
  for event_ref in person.get_event_ref_list():
    if int(event_ref.get_role()) == EventRoleType.PRIMARY:
      event = db.get_event_from_handle(event_ref.ref)
      if event.get_type() == event_type:
        return event
  return None

def ligi_gr_fs(db,grPersono,fsid):
  attr = None
  with DbTxn(_("Aldoni FamilySearch ID"), db) as txn:
    for attr in grPersono.get_attribute_list():
      if attr.get_type() == '_FSFTID':
        attr.set_value(fsid)
        break
    if not attr :
      attr = Attribute()
      attr.set_type('_FSFTID')
      attr.set_value(fsid)
      grPersono.add_attribute(attr)
    db.commit_person(grPersono,txn)
