from functools import update_wrapper
from django.contrib.admin.util import unquote
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.utils.translation import ugettext as _

__author__ = 'aldaran'


from django.contrib.admin import site, ModelAdmin
from colf.bustapaga.models import *


class ReadOnlyModelAdmin(ModelAdmin):

    def readonly_permission(self, *args, **kwargs):
        return False

    has_add_permission = has_delete_permission = readonly_permission

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

class MeseAdmin(ModelAdmin):
    list_display = ["contratto", "__str__", "elaborato", "calcola", "visualizza", "annulla"]
    # actions = ["calcola_bustapaga", "rimuovi_bustapaga"]
    list_filter = ["contratto__dip", "contratto__dl", "mese", "anno"]

    fieldsets = (
        ('Mese', {'fields' : ('contratto', 'anno', 'mese', 'giorni_lavorabili')},),
        ('Lavotate', {'fields' : ('ore_lavorate','straordinario_25', 'straordinario_50', 'straordinario_60')},),
        ('Ferie', {'fields' : ('giorni_ferie_goduti',)},),
        ('Permessi', {'fields' : ('ore_permessi', 'permessi_per_lutto_o_visite_mediche', 'permessi_matrimoniali')},),
        ('Anticipi', {'fields' : ('anticipo_tfr',)},),
        )

    def calcola(self, obj):
        return "<a href='calcola/%s'>%s</a>" % (obj.pk, "Ricalcola" if obj.elaborato() else "Calcola")
    calcola.allow_tags = True

    def visualizza(self, obj):
        return "" if not obj.elaborato() else "<a href='preview/%s'>Visualizza</a>" % obj.pk
    visualizza.allow_tags = True

    def annulla(self, obj):
        return "" if not obj.annullabile() else "<a href='annulla/%s'>Annulla</a>" % obj.pk
    annulla.allow_tags = True


    def calcola_bustapaga(self, request, qs):
        for mese in qs:
            BustaPaga.objects.calcola(mese)
            StatoContrattuale.objects.calcola(mese)

    def rimuovi_bustapaga(self, request, qs):
        BustaPaga.objects.filter(mese__in=qs).delete()
        StatoContrattuale.objects.filter(mese__in=qs).delete()

    def calcola_view(self, request, object_id, extra_context=None):
        model = self.model
        opts = model._meta
        obj = self.get_object(request, unquote(object_id))
        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(opts.verbose_name), 'key': escape(object_id)})
        BustaPaga.objects.calcola(obj)
        StatoContrattuale.objects.calcola(obj)
        self.message_user(request, "Busta paga %s calcolata" % obj.contratto)
        return HttpResponseRedirect("../..")

    def annulla_view(self, request, object_id, extra_context=None):
        model = self.model
        opts = model._meta
        obj = self.get_object(request, unquote(object_id))
        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(opts.verbose_name), 'key': escape(object_id)})
        BustaPaga.objects.filter(mese=obj).delete()
        StatoContrattuale.objects.filter(mese=obj).delete()
        self.message_user(request, "Busta paga %s annullata" % obj.contratto)
        return HttpResponseRedirect("../..")

    def preview_view(self, request, object_id, extra_context=None):
        model = self.model
        opts = model._meta

        obj = self.get_object(request, unquote(object_id))

        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(opts.verbose_name), 'key': escape(object_id)})

        context = {
            'title': _('Preview %s') % force_unicode(opts.verbose_name),
            'object_id': object_id,
            'original': obj,
            'is_popup': "_popup" in request.REQUEST,
            'app_label': opts.app_label,
            'mese' : obj
            }
        context.update(extra_context or {})

        return TemplateResponse(request, "bustapaga.html", context, current_app=self.admin_site.name)


    def get_urls(self):
        from django.conf.urls import patterns, url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.module_name

        urlpatterns = patterns('',
            url(r'^preview/(.+)/$', wrap(self.preview_view), name='%s_%s_preview' % info),
            url(r'^calcola/(.+)/$', wrap(self.calcola_view), name='%s_%s_calcola' % info),
            url(r'^annulla/(.+)/$', wrap(self.annulla_view), name='%s_%s_annulla' % info),
        ) + super(MeseAdmin, self).get_urls()

        return urlpatterns

class VersamentoAdmin(ModelAdmin):
    list_display = ["contratto", "anno", "trimestre", "importo_cassa_malattia", "importo_contributi", "importo_totale"]
    # actions = ["calcola_bustapaga", "rimuovi_bustapaga"]
    list_filter = ["contratto__dip", "contratto__dl", "anno", "trimestre"]
    total_functions = {'importo_cassa_malattia': sum, "importo_contributi": sum, "importo_totale": sum}
    change_list_template = "admin/change_list_with_totals.html"

site.register(DatoreLavoro)
site.register(Dipendente)
site.register(Contratto)
site.register(Luogo)
site.register(Localita)
site.register(Mese, MeseAdmin)
site.register(Versamento, VersamentoAdmin)

class BustaPagaAdmin(ReadOnlyModelAdmin):
    list_display = ["mese", "contratto", "totale_lordo", "totale_trattenute", "arrotondamento", "netto_pagato"]
    total_functions = {'totale_lordo': sum, "totale_trattenute": sum, "netto_pagato": sum}
    change_list_template = "admin/change_list_with_totals.html"

site.register(BustaPaga, BustaPagaAdmin)
#site.register(StatoContrattuale, ReadOnlyModelAdmin)
