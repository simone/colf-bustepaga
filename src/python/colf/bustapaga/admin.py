from functools import update_wrapper
from django.contrib.admin.util import unquote
from django.http import Http404
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
    actions = ["calcola_bustapaga", "rimuovi_bustapaga"]

    def calcola_bustapaga(self, request, qs):
        for mese in qs:
            BustaPaga.objects.calcola(mese)
            StatoContrattuale.objects.calcola(mese)

    def rimuovi_bustapaga(self, request, qs):
        BustaPaga.objects.filter(mese__in=qs).delete()
        StatoContrattuale.objects.filter(mese__in=qs).delete()

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
            url(r'^preview/(.+)/$',
                wrap(self.preview_view),
                name='%s_%s_preview' % info),
        ) + super(MeseAdmin, self).get_urls()

        return urlpatterns



site.register(DatoreLavoro)
site.register(Dipendente)
site.register(Contratto)
site.register(Luogo)

site.register(Mese, MeseAdmin)
site.register(BustaPaga, ReadOnlyModelAdmin)
site.register(StatoContrattuale, ReadOnlyModelAdmin)