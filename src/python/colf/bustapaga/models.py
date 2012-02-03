from decimal import Decimal
from django.db import models

from django.contrib.localflavor.it.forms import ITSocialSecurityNumberField, ITZipCodeField
from django.utils.dates import MONTHS
from django.utils.functional import cached_property

from colf.bustapaga.managers import BustaPagaManager, StatoContrattualeManager
from copy import copy

class CF(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 16)
        super(CF, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault("form_class", ITSocialSecurityNumberField)
        return super(CF, self).formfield(**kwargs)

class Luogo(models.Model):
    comune = models.CharField(max_length=200)
    provincia  = models.CharField(max_length=2)
    regione = models.CharField(max_length=3)
    cap = models.CharField(max_length=5)
    via = models.CharField(max_length=200)
    numero = models.CharField(max_length=10)

    def __unicode__(self):
        return "%s, %s %s %s (%s)" % (
            self.via, self.numero, self.cap, self.comune, self.provincia
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
    pass

class Dipendente(Persona):
    pass


class Contratto(models.Model):
    dl = models.ForeignKey(DatoreLavoro)
    dip = models.ForeignKey(Dipendente)
    data_assunzione = models.DateField()
    mansione = models.CharField(max_length=200)
    codice_inps = models.CharField(max_length=200)
    livello = models.CharField(max_length=2, choices=(("A","A"),("B","B")))

    paga_base = models.DecimalField(max_digits=11, decimal_places=2)
    paga_scatti = models.DecimalField(max_digits=11, decimal_places=2)
    paga_superminimo = models.DecimalField(max_digits=11, decimal_places=2)

    @property
    def quota_oraria_trattenuta_inps(self):
        return Decimal("1.54") if self.paga_oraria_effettiva>Decimal("7.34") else Decimal("1.36")

    @property
    def quota_oraria_dip_trattenuta_inps(self):
        return Decimal("0.37") if self.paga_oraria_effettiva>Decimal("7.34") else Decimal("0.33")

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

class YearField(models.PositiveSmallIntegerField):
    def formfield(self, **kwargs):
        defaults = {'min_value': 1900, 'max_value': 9999}
        defaults.update(kwargs)
        return super(YearField, self).formfield(**defaults)

class Mese(models.Model):
    anno = YearField()
    mese = models.SmallIntegerField(choices=MONTHS.items())

    contratto = models.ForeignKey(Contratto)

    giorni_lavorabili = models.SmallIntegerField()
    giorni_festivita = models.SmallIntegerField()

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
        a, m = (self.anno, self.mese) if self.mese > 1 else (self.anno-1, 12)
        return self.contratto.mese_set.get(anno=a, mese=m)

    @property
    def has_mese_successivo(self):
        try:
            self.mese_precedente
        except:
            return False
        return True

    @cached_property
    def mese_successivo(self):
        a, m = (self.anno, self.mese) if self.mese < 12 else (self.anno+1, 1)
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

    def __unicode__(self):
        return unicode(self.mese)

    def makecopy(self, *kwargs):
        new = copy(self)
        for k,v in kwargs.items():
            setattr(new, k, v)
        return new


# bozza
class Versamento(models.Model):
    contratto = models.ForeignKey(Contratto)
    trimestre = models.SmallIntegerField(
        choices=((1,"Primo Trimestre"),(2,"Secondo Trimestre"),(3,"Terzo Trimestre"),(4,"Quarto Trimestre"))
    )
