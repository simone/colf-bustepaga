# -*- coding: utf-8 -*-
from decimal import Decimal
from django.db import models

__author__ = 'aldaran'


class BustaPagaManager(models.Manager):

    def calcola(self, mese):
        self.filter(mese=mese).delete()
        obj = self.model(mese=mese)

        # ordinario
        obj.paga_ore_lavorate = mese.ore_lavorate * mese.contratto.paga_oraria
        quota_giornaliera = obj.paga_ore_lavorate / 26

        obj.paga_straordinario_25 = mese.straordinario_25 * mese.contratto.paga_oraria * Decimal("1.25")
        obj.paga_straordinario_50 = mese.straordinario_50 * mese.contratto.paga_oraria * Decimal("1.50")
        obj.paga_straordinario_60 = mese.straordinario_60 * mese.contratto.paga_oraria * Decimal("1.60")

        #if mese.ore_lavorate_durante_festivita>0:
        #    pass

        ore_lavorabili = mese.giorni_lavorabili * mese.contratto.ore_giornaliere
        ore_non_lavorate=ore_lavorabili-mese.ore_lavorate-mese.giorni_ferie_goduti

        if mese.giorni_ferie_goduti>0:
            # calcolo ferie/permessi
            obj.paga_ferie = mese.giorni_ferie_goduti * mese.contratto.retribuzione_giornaliera_globale_di_fatto
        else:
            obj.paga_ferie = 0

        if ore_non_lavorate>0:
            # non è venuta.... o ha fatto meno ore che si fa?
            # permessi
            pass
        elif ore_non_lavorate<0:
            # straordinario
            pass

        if mese.giorni_festivita>0:
            obj.paga_festivita = mese.giorni_festivita * mese.contratto.retribuzione_giornaliera_globale_di_fatto
            #if mese.giorni_festivita_domenica>0:
            #    obj.paga_festivita += mese.giorni_festivita_domenica * quota_giornaliera_di_fatto
        else:
            obj.paga_festivita = 0

        obj.anticipo_tfr = mese.anticipo_tfr

        if mese.mese == 13:
            obj.paga_tredicesima = sum([busta.totale_lordo-busta.anticipo_tfr for busta in self.filter(mese__anno=mese.anno, mese__mese__in=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])])/12
        else:
            obj.paga_tredicesima = 0

        obj.ore_retribuite = mese.ore_lavorate + (obj.paga_festivita + obj.paga_straordinario) / mese.contratto.paga_oraria + mese.ore_ferie_godute

        obj.trattenuta_inps = obj.ore_retribuite*mese.contratto.quota_oraria_dip_trattenuta_inps
        obj.trattenuta_cassa_colf = obj.ore_retribuite*mese.contratto.quota_oraria_dip_trattenuta_malattia

        obj.arrotondamento_mese_precedente = -mese.mese_precedente.bustapaga.arrotondamento \
            if mese.has_mese_precedente else 0

        netto = obj.totale_lordo - obj.totale_trattenute + obj.arrotondamento_mese_precedente
        rounded = netto.quantize(1)
        obj.arrotondamento = rounded - netto

        obj.save()


class StatoContrattualeManager(models.Manager):

    def calcola(self, mese):
        self.filter(mese=mese).delete()

        obj = self.model(mese=mese) if not mese.has_mese_precedente else \
            mese.mese_precedente.statocontrattuale.makecopy(pk=None, mese=mese)

        if mese.mese == 12: # il tfr_annuo lo calcolo su dicembre
            tfr_annuo = sum([busta.totale_lordo-busta.anticipo_tfr for busta in mese.bustapaga.__class__.objects.filter(mese__anno=mese.anno)])/Decimal("13.5")
            obj.tfr_quota_mese = tfr_annuo - obj.tfr_accumulato
            obj.tfr_accumulato = tfr_annuo
        else:
            obj.tfr_quota_mese = mese.bustapaga.calcolo_tfr_quota_mese
            obj.tfr_accumulato += obj.tfr_quota_mese

        obj.tfr_anticipato += mese.anticipo_tfr

        if mese.mese < 13:

            obj.ore_ferie_dovute += mese.contratto.rateo_mensile_ore_ferie
            obj.ore_ferie_godute += mese.ore_ferie_godute

            obj.cassa_colf_dl += mese.bustapaga.ore_retribuite*mese.contratto.quota_oraria_dl_trattenuta_malattia
            obj.cassa_colf_dip += mese.bustapaga.trattenuta_cassa_colf

            obj.contributi_inps_dl += mese.bustapaga.ore_retribuite*mese.contratto.quota_oraria_dl_trattenuta_inps
            obj.contributi_inps_dip += mese.bustapaga.trattenuta_inps

        obj.save()
