from django.db import models

__author__ = 'aldaran'


class BustaPagaManager(models.Manager):

    def calcola(self, mese):
        self.filter(mese=mese).delete()
        obj = self.model(mese=mese)

        # ordinario
        obj.paga_ore_lavorate = mese.ore_lavorate * mese.contratto.paga_oraria
        quota_giornaliera = obj.paga_ore_lavorate / 26

        #if mese.ore_lavorate_durante_festivita>0:
        #    pass

        ore_lavorabili = mese.giorni_lavorabili * mese.contratto.ore_giornaliere
        ore_non_lavorate=ore_lavorabili-mese.ore_lavorate

        if ore_non_lavorate>0:
            # calcolo ferie/permessi
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

        obj.ore_retribuite = mese.ore_lavorate + obj.paga_festivita / mese.contratto.paga_oraria
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

        obj.tfr_quota_mese = mese.bustapaga.calcolo_tfr_quota_mese
        obj.tfr_accumulato += obj.tfr_quota_mese
        obj.tfr_anticipato += mese.anticipo_tfr

        obj.ore_ferie_dovute += mese.contratto.rateo_mensile_ore_ferie
        obj.ore_ferie_godute += mese.giorni_ferie_goduti

        obj.cassa_colf_dl += mese.bustapaga.ore_retribuite*mese.contratto.quota_oraria_dl_trattenuta_malattia
        obj.cassa_colf_dip += mese.bustapaga.trattenuta_cassa_colf

        obj.contributi_inps_dl += mese.bustapaga.ore_retribuite*mese.contratto.quota_oraria_dl_trattenuta_inps
        obj.contributi_inps_dip += mese.bustapaga.trattenuta_inps

        obj.save()
