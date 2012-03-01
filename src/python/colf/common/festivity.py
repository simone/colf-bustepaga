# -*- coding: utf-8 -*-

import datetime
from dateutil.easter import *

__author__ = 'aldaran'

try:
    from django.utils.translation import gettext
    gettext("ok")
except:
    gettext = lambda text:text

_ = lambda text: gettext(text)

patroni_callbacks = set()
PATRONI = {}


ROMA = "Roma"


def festivita_italiane(year, citta=ROMA, month=None):
    """
    DATA, NOME FESTA, DOMENICA?
    """
    return tuple((d, s, d.weekday()==6) for d,s in sorted((
        (datetime.date(year,  1,  1), _("Capodanno")),
        (datetime.date(year,  1,  6), _("Epifania")),
        (pasquetta(year),             _("Lunedi dell'Angelo")),
        (datetime.date(year,  4, 25), _("Anniversario della Liberazione")),
        (datetime.date(year,  5,  1), _("Festa del Lavoro")),
        (datetime.date(year,  6,  2), _("Festa della Repubblica")),
        (datetime.date(year,  8, 15), _("Assunzione di Maria Vergine")),
        (datetime.date(year, 11,  2), _("Tutti i Santi")),
        (datetime.date(year, 12,  8), _("Immacolata Concezione")),
        (datetime.date(year, 12, 25), _("Natale")),
        (datetime.date(year, 12, 26), _("Santo Stefano")),
        patrono(year, citta)
    )) if not month or d.month==month)


def pasquetta(year):
    return easter(int(year)) + datetime.timedelta(1)

def patrono(year, citta):
    for callback in patroni_callbacks:
        results = callback(year, citta)
        if len(results) == 2:
            giorno, festa = results
            return (giorno, _(festa))
    try:
        mese, giorno, festa = PATRONI.get(citta)
        return (datetime.date(year,  mese,  giorno), _(festa))
    except:
        raise Exception("""Patrono non trovato per %(citta)s
        registrare prima il santo patrono di %(citta)s
        registra_patrono("%(citta)s", "s.patrono", giorno, mese)
        """ % {'citta':citta})

def registra_gettext(new_gettext):
    global gettext
    gettext = new_gettext

def registra_patrono(citta, mese, giorno, festa):
    PATRONI[citta] = mese, giorno, festa

def registra_patroni(*args, **kwargs):
    try:
        for arg in args:
            if isinstance(arg, dict):
                for citta, v in arg.items():
                    registra_patrono(citta, *v)
            elif isinstance(arg, (list,tuple)):
                if len(arg)==4 and isinstance(arg[0], (str, unicode)):
                    registra_patrono(*arg)
                else:
                    registra_patroni(*arg)
            for citta, v in kwargs.items():
                registra_patrono(citta, *v)
    except:
        raise Exception("""USE:
        registra_patroni(dict)
        registra_patroni(list)
        registra_patroni(**dict)
        registra_patroni(*list)

        dove dict ha questo formato
          {'Roma': (6, 29, 'Santi Pietro e Paolo')}
        e list ho questo formato:
          [("Roma", 6, 29, 'Santi Pietro e Paolo'), ("B", 2, 2, "Santo B")]
        """)

def registra_patrono_datasource(callback):
    """
    giorno, festa = calback(anno, citta)
    """
    patroni_callbacks.add(callback)


registra_patrono(ROMA, 6, 29, "Santi Pietro e Paolo")