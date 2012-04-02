# -*- coding: utf-8 -*-

from decimal import Decimal
import datetime
from django.db import models

from django.contrib.localflavor.it.forms import ITSocialSecurityNumberField, ITZipCodeField
from django.utils.dates import MONTHS
from django.utils.functional import cached_property

from colf.bustapaga.managers import BustaPagaManager, StatoContrattualeManager
from colf.common import festivity
from copy import copy

class CF(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 16)
        super(CF, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault("form_class", ITSocialSecurityNumberField)
        return super(CF, self).formfield(**kwargs)

class YearField(models.PositiveSmallIntegerField):
    def formfield(self, **kwargs):
        defaults = {'min_value': 1900, 'max_value': 9999}
        defaults.update(kwargs)
        return super(YearField, self).formfield(**defaults)

class Localita(models.Model):
    nome = models.CharField(max_length=200)
    comune = models.CharField(max_length=200)
    provincia  = models.CharField(max_length=2)
    regione = models.CharField(max_length=3)
    patrono = models.CharField(max_length=200)
    giorno_patrono = models.DateField(help_text=("L'anno verrà ignorato"))

    @property
    def full_name(self):
        return self.comune if self.comune==self.nome else "%s (%s)" % (self.comune, self.nome)

    def get_patrono(self, anno=None):
        return datetime.date(anno,
            self.giorno_patrono.month,
            self.giorno_patrono.day) if anno else self.giorno_patrono, self.patrono

    class Meta:
        verbose_name_plural = "Localita"

    def __unicode__(self):
        return "%s, (%s) [%s,%s]" % (
            self.full_name, self.provincia, self.regione, self.patrono
            )

class Luogo(models.Model):
    localita = models.ForeignKey(Localita)
    cap = models.CharField(max_length=5)
    via = models.CharField(max_length=200)
    numero = models.CharField(max_length=10)

    class Meta:
        verbose_name_plural = "Luoghi"

    def __unicode__(self):
        return "%s, %s %s %s" % (
            self.via, self.numero, self.cap, self.localita
        )


class Persona(models.Model):
    nome = models.CharField(max_length=200)
    cognome = models.CharField(max_length=200)
    cf = CF()
    indirizzo = models.ForeignKey(Luogo)

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.cf


class DatoreLavoro(Persona):
    class Meta:
        verbose_name = "Datore di lavoro"
        verbose_name_plural = "Datori di lavoro"


class Dipendente(Persona):
    class Meta:
        verbose_name_plural = "Dipendenti"


class TabellaINPS(object):
    def __init__(self, tabella, oltre_24_ore):
        self.tabella = [[Decimal(x) if x else x for x in t] for t in tabella]
        self.oltre_24_ore = [Decimal(x) for x in oltre_24_ore]

    def _find_line(self, paga_oraria_effettiva, ore_settimanali, cuaf):
        if ore_settimanali>24:
            conv, c_tot_cuaf, c_dip_cuaf, c_tot, c_dip = self.oltre_24_ore

        else:
            for m, M, conv, c_tot_cuaf, c_dip_cuaf, c_tot, c_dip in self.tabella:
                if M and m < paga_oraria_effettiva <= M:
                    break

        _tot = c_tot_cuaf if cuaf else c_tot
        _dip = c_dip_cuaf if cuaf else c_dip
        return conv, _tot, _dip

    def paga_convenzionale(self, paga_oraria_effettiva, ore_settimanali, cuaf=False):
        return self._find_line(paga_oraria_effettiva, ore_settimanali, cuaf)[0]

    def quota_oraria_trattenuta_inps(self, paga_oraria_effettiva, ore_settimanali, cuaf=False):
        return self._find_line(paga_oraria_effettiva, ore_settimanali, cuaf)[1]

    def quota_oraria_dip_trattenuta_inps(self, paga_oraria_effettiva, ore_settimanali, cuaf=False):
        return self._find_line(paga_oraria_effettiva, ore_settimanali, cuaf)[2]


TABELLA_INPS = {
    2012 : TabellaINPS((
        # DECORRENZA DAL 1 GENNAIO 2012 AL 31 DICEMBRE 2012
        # LAVORATORI ITALIANI E STRANIERI
        # IMPORTO CONTRIBUTO ORARIO Effettiva e Convenzionale
        # Comprensivo quota CUAF e Senza quota CUAF (1)
        (   "0",     "7.54", "6.68", "1.40", "0.34", "1.41", "0.34"),
        ("7.54",     "9.19", "7.54", "1.58", "0.38", "1.59", "0.38"),
        ("9.19", "Infinity", "9.19", "1.93", "0.46", "1.94", "0.46")),
        # Orario di lavoro superiore a 24 ore settimanali
        (            "4.85", "1.02", "0.24", "1.02", "0.24"),
    )
}


class Contratto(models.Model):
    dl = models.ForeignKey(DatoreLavoro)
    dip = models.ForeignKey(Dipendente)
    sede = models.ForeignKey(Luogo)
    data_assunzione = models.DateField()
    mansione = models.CharField(max_length=200)
    codice_inps = models.CharField(max_length=200)
    codice_rapporto = models.CharField(max_length=200)
    livello = models.CharField(max_length=2, choices=(("A","A"),("B","B")))
    cassa_malattia = models.CharField(max_length=2, choices=(("F2", "Cassa Colf"),("E1", "Ebilcoba")))

    paga_base = models.DecimalField(max_digits=11, decimal_places=2)
    paga_scatti = models.DecimalField(max_digits=11, decimal_places=2)
    paga_superminimo = models.DecimalField(max_digits=11, decimal_places=2)

    class Meta:
        verbose_name_plural = "Contratti"

    @property
    def quota_oraria_trattenuta_inps(self):
        return TABELLA_INPS[2012].quota_oraria_trattenuta_inps(self.paga_oraria_effettiva, self.ore_settimanali)

    @property
    def quota_oraria_dip_trattenuta_inps(self):
        return TABELLA_INPS[2012].quota_oraria_dip_trattenuta_inps(self.paga_oraria_effettiva, self.ore_settimanali)

    @property
    def quota_oraria_dl_trattenuta_inps(self):
        return self.quota_oraria_trattenuta_inps - self.quota_oraria_dip_trattenuta_inps

    quota_oraria_dip_trattenuta_malattia = models.DecimalField(max_digits=11, decimal_places=2)
    quota_oraria_dl_trattenuta_malattia = models.DecimalField(max_digits=11, decimal_places=2)

    @property
    def paga_oraria(self):
        return self.paga_base + self.paga_scatti + self.paga_superminimo

    @property
    def paga_oraria_effettiva(self):
        return self.paga_oraria * 13/12

    ore_giornaliere = models.SmallIntegerField(default=4)
    giorni_lavorativi_settimanali = models.SmallIntegerField(default=1)

    @property
    def ore_settimanali(self):
        return self.ore_giornaliere * self.giorni_lavorativi_settimanali

    @property
    def media_paga_settimanale(self):
        return self.paga_oraria * self.ore_settimanali

    @property
    def media_paga_annuale(self):
        return self.media_paga_settimanale * 52

    @property
    def media_paga_mensile(self):
        return self.media_paga_annuale / 12

    @property
    def media_paga_13_mesi(self):
        return self.media_paga_mensile * 13

    @property
    def calcolo_tfr_annuale(self):
        return self.media_paga_13_mesi / Decimal("13.5")

    @property
    def retribuzione_giornaliera_globale_di_fatto(self):
        return self.media_paga_mensile / 26

    @property
    def ferie_ore_spettanti_annuali(self):
        return Decimal("4.333") * self.ore_settimanali

    @property
    def rateo_mensile_ore_ferie(self):
        return self.ferie_ore_spettanti_annuali / 12

    @cached_property
    def mese_corrente(self):
        try:
            return self.mese_set.all().order_by("-anno", "-mese")[0]
        except Exception, e:
            print e
        return None

    def __unicode__(self):
        return u"%s (%s)" % (
            self.dip, self.dl
        )




class Mese(models.Model):
    anno = YearField()
    mese = models.SmallIntegerField(choices=MONTHS.items())

    contratto = models.ForeignKey(Contratto)

    giorni_lavorabili = models.SmallIntegerField()

    @cached_property
    def giorni_festivita(self):
        if self.anno and self.mese and self.contratto:
            return len(festivity.festivita_italiane(self.anno, self.contratto.sede.localita.nome, self.mese))
        return 0

    class Meta:
        verbose_name = "Mese lavorato"
        verbose_name_plural = "Mesi lavorati"

    def elaborato(self):
        try:
            return bool(self.bustapaga and self.statocontrattuale)
        except:
            return False
    elaborato.boolean = True

    def annullabile(self):
        return self.elaborato() and not self.has_mese_successivo
    annullabile.boolean = True

    @property
    def giorni_ferie_goduti(self):
        return 0

    ore_lavorate = models.DecimalField(max_digits=11, decimal_places=2)
    anticipo_tfr = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal(0))

    @property
    def has_mese_precedente(self):
        try:
            self.mese_precedente
        except:
            return False
        return True

    @cached_property
    def mese_precedente(self):
        a, m = (self.anno, self.mese-1) if self.mese > 1 else (self.anno-1, 12)
        print self.anno, self.mese, a, m, self.mese > 1
        return self.contratto.mese_set.get(anno=a, mese=m)

    @property
    def has_mese_successivo(self):
        try:
            self.mese_successivo
        except:
            return False
        return True

    @cached_property
    def mese_successivo(self):
        a, m = (self.anno, self.mese+1) if self.mese < 12 else (self.anno+1, 1)
        return self.contratto.mese_set.get(anno=a, mese=m)

    def __unicode__(self):
        return u"%s %s" % (self.get_mese_display(), self.anno)


class BustaPaga(models.Model):
    mese = models.OneToOneField(Mese)
    objects = BustaPagaManager()

    ore_retribuite = models.DecimalField(max_digits=11, decimal_places=2)

    #retribuzione_mensile_di_fatto
    paga_ore_lavorate = models.DecimalField(max_digits=11, decimal_places=2)
    paga_festivita = models.DecimalField(max_digits=11, decimal_places=2)

    @property
    def calcolo_tfr_quota_mese(self):
        return self.paga_ore_lavorate / Decimal("13.5")

    @property
    def totale_lordo(self):
        return self.paga_festivita + self.paga_ore_lavorate

    trattenuta_inps = models.DecimalField(max_digits=11, decimal_places=2)
    trattenuta_cassa_colf = models.DecimalField(max_digits=11, decimal_places=2)

    @property
    def totale_trattenute(self):
        return self.trattenuta_inps + self.trattenuta_cassa_colf

    arrotondamento_mese_precedente = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal(0))
    arrotondamento = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal(0))

    @property
    def netto_pagato(self):
        return self.totale_lordo - self.totale_trattenute \
               + self.arrotondamento_mese_precedente + self.arrotondamento

    @property
    def contratto(self):
        return self.mese.contratto

    class Meta:
        verbose_name_plural = "Buste paga"

    def __unicode__(self):
        return unicode(self.mese)


class StatoContrattuale(models.Model):
    mese = models.OneToOneField(Mese)
    objects = StatoContrattualeManager()

    tfr_anticipato = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal(0))
    tfr_accumulato = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal(0))
    tfr_quota_mese = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal(0))

    ore_ferie_dovute = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal(0))
    ore_ferie_godute = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal(0))

    @property
    def ore_ferie_residue(self):
        return self.ore_ferie_dovute - self.ore_ferie_godute

    @property
    def giorni_ferie_residue(self):
        return self.ore_ferie_residue * 26 / self.mese.contratto.ferie_ore_spettanti_annuali

    cassa_colf_dl = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal(0))
    cassa_colf_dip = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal(0))

    @property
    def totale_cassa_colf(self):
        return self.cassa_colf_dl + self.cassa_colf_dip

    contributi_inps_dl = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal(0))
    contributi_inps_dip = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal(0))

    @property
    def totale_contributi_inps(self):
        return self.contributi_inps_dl + self.contributi_inps_dip

    class Meta:
        verbose_name_plural = "Stati Contrattuali"

    def __unicode__(self):
        return unicode(self.mese)

    def makecopy(self, **kwargs):
        new = copy(self)
        for k,v in kwargs.items():
            setattr(new, k, v)
        return new


# bozza
class Versamento(models.Model):
    contratto = models.ForeignKey(Contratto)
    anno = YearField()
    trimestre = models.SmallIntegerField(
        choices=((1,"Primo Trimestre"),(2,"Secondo Trimestre"),(3,"Terzo Trimestre"),(4,"Quarto Trimestre"))
    )
    data_versamento = models.DateField()
    codice_banca = models.CharField(max_length=200)

    ore_intere_retribuite = models.SmallIntegerField()
    resto_ore_retribuite = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal(0)) # da pagare il trimestre successivo
    retribuzione_oraria_effettiva = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal(0))
    importo_cassa_malattia = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal(0))
    importo_contributi = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal(0))

    @property
    def importo_totale(self):
        return self.importo_cassa_malattia + self.importo_contributi
    
    class Meta:
        verbose_name_plural = "Versamenti"


    def __unicode__(self):
        return "%s %s-%s" %(unicode(self.contratto), self.trimestre, self.anno)

def patrono(anno, citta):
    try:
        loc = Localita.objects.get(nome=citta)
        return loc.get_patrono(anno)
    except:
        pass
festivity.registra_patrono_datasource(patrono)