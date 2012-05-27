__author__ = 'aldaran'


from django.template import Library

register = Library()

def totals_row(cl):
    total_functions = getattr(cl.model_admin, 'total_functions', {})
    totals = []
    for field_name in cl.list_display:
        if field_name in total_functions:
            values = [getattr(i, field_name) for i in cl.result_list]
            totals.append(total_functions[field_name](values))
        else:
            totals.append('')
    return {'cl': cl, 'totals_row': totals}
totals_row = register.inclusion_tag("totals_row.html")(totals_row)