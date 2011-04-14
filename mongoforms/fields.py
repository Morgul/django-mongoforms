from operator import itemgetter
from django import forms
from django.utils.encoding import smart_unicode
from pymongo.errors import InvalidId
from pymongo.objectid import ObjectId

LISTFIELD_ITEM_LABEL = "listfield-items"
DICTFIELD_ITEM_LABEL = "dictfield-item"
DICTFIELD_ITEM_LABEL_VALUE_SUFFIX = "-value"
HIDE_ADD_JS_SCRIPT = """
<script type="text/javascript" src="https://ajax.googleapis.com/ajax/libs/jquery/1.5.2/jquery.min.js"></script>
<script type="text/javascript">
$(function(){
    $(".field-item").append('<input type="button" class="field-item-delete" value="X">')
    $(".field-item-delete").click(function(){
        $(":input",$(this).parent()).val("");
        $(this).parent().hide();
    })

    $('.field-item-new').before('<input type="button" class="field-item-add" value="add">').hide()

    $('.field-item-add').click(function(){
        $(this).next().show();
        $(this).hide();
    })
})
</script>
"""


import re



class DictWidget(forms.Widget):

    def __init__(self, extra, *aargs, **kwaargs):
        forms.Widget.__init__(self, *aargs, **kwaargs)
        self.__inner_widget = forms.TextInput()
        self.extra = extra

    def render(self, name, value, attrs=None):
        rend_key = lambda i,v: self.__inner_widget.render("%s-%s-%i"%(DICTFIELD_ITEM_LABEL, name,i), v, attrs)
        rend_value = lambda i,v: self.__inner_widget.render("%s-%s-%i%s"%(DICTFIELD_ITEM_LABEL, name,i, DICTFIELD_ITEM_LABEL_VALUE_SUFFIX), v, attrs)

        r = '<br>\n'.join(['<div class="field-item">'+rend_key(i,v[0])+rend_value(i,v[1])+'</div>' for i, v in enumerate(value.items())])
        r += '<br>\n'+'<br>\n'.join(['<div class="field-item-new field-item">(new)'+rend_key(i,v[0])+rend_value(i,v[1])+'</div>' for i, v in enumerate([("","")]*self.extra,len(value.keys()))])
        return r+HIDE_ADD_JS_SCRIPT




class DictField(forms.Field):
    """
    Field for DictField.
    """
    __r_pattern= re.compile( ur"^%s-(.+)-(\d+)$"%DICTFIELD_ITEM_LABEL, re.IGNORECASE)
    @classmethod
    def prepare_form_data(cls, data):
        list_data = {}
        for key, value in data.items():
            m = cls.__r_pattern.match(key)
            if m is not None:
                try:
                    list_data[m.groups()[0]]
                except KeyError:
                    list_data[m.groups()[0]]={}
                list_data[m.groups()[0]][data[key]]=data[key+DICTFIELD_ITEM_LABEL_VALUE_SUFFIX]
        print list_data
        new_data = data.copy()
        new_data.update(list_data)
        return new_data

    def __init__(self, extra=1, *aargs, **kwaargs):
        forms.Field.__init__(self, widget=DictWidget(extra=extra), *aargs, **kwaargs)

    def clean(self, value):
        for key in value.keys():
            if key is None or len(key)==0:
                del value[key]
        return value


class ListWidget(forms.Widget):

    def __init__(self, inner_widget, extra, *aargs, **kwaargs):
        forms.Widget.__init__(self, *aargs, **kwaargs)
        self.__inner_widget = inner_widget
        self.extra = extra
        
    def render(self, name, value, attrs=None):
        rend = lambda i,v: self.__inner_widget.render("%s-%s-%i"%(LISTFIELD_ITEM_LABEL, name,i), v, attrs)
        r = '<br>\n'.join(['<div class="field-item">'+rend(i,v)+'</div>' for i, v in enumerate(value)])
        r += '<br>\n'+'<br>\n'.join(['<div class="field-item field-item-new">(new)'+rend(i,v)+'</div>' for i, v in enumerate([None]*self.extra,len(value))])
        return r+HIDE_ADD_JS_SCRIPT


class ListField(forms.Field):
    """
    Field for ListField.
    """
    __r_pattern = re.compile( ur"^%s-(.+)-(\d+)$"%LISTFIELD_ITEM_LABEL, re.IGNORECASE)
    @classmethod
    def prepare_form_data(cls, data):
        list_data = {}
        for key, value in data.items():
            m = cls.__r_pattern.match(key)
            if m is not None:
                try:
                    list_data[m.groups()[0]]
                except KeyError:
                    list_data[m.groups()[0]]=[]
                list_data[m.groups()[0]].append([value, int(m.groups()[1])])
        for key, value in list_data.items():
            newvalue = [v for v,index in sorted(value, key=itemgetter(1))]
            list_data[key] = newvalue
        new_data = data.copy()
        new_data.update(list_data)
        return new_data

    def __init__(self, inner_field, extra=1, *aargs, **kwaargs):
        self.__inner_field = MongoFormFieldGenerator().generate("somename", inner_field)
        forms.Field.__init__(self, widget=ListWidget(inner_widget=self.__inner_field.widget, extra=extra), *aargs, **kwaargs)

    def clean(self, value):
        print value
        return [self.__inner_field.clean(v) for v in value if (v is not None) and (len(v)>0)]


class ReferenceField(forms.ChoiceField):
    """
    Reference field for mongo forms. Inspired by `django.forms.models.ModelChoiceField`.
    """
    def __init__(self, queryset, *aargs, **kwaargs):
        forms.Field.__init__(self, *aargs, **kwaargs)
        self.queryset = queryset

    def _get_queryset(self):
        return self._queryset

    def _set_queryset(self, queryset):
        self._queryset = queryset
        self.widget.choices = self.choices

    queryset = property(_get_queryset, _set_queryset)

    def _get_choices(self):
        if hasattr(self, '_choices'):
            return self._choices

        self._choices = [(obj.id, smart_unicode(obj)) for obj in self.queryset]
        return self._choices

    choices = property(_get_choices, forms.ChoiceField._set_choices)

    def clean(self, value):
        try:
            print "val", value
            oid = ObjectId(value)
            print oid
            oid = super(ReferenceField, self).clean(oid)
            print oid
            obj = self.queryset.get(id=oid)
            print obj
        except (TypeError, InvalidId, self.queryset._document.DoesNotExist):
            raise forms.ValidationError(self.error_messages['invalid_choice'] % {'value':value})
        return obj

class MongoFormFieldGenerator(object):
    """This class generates Django form-fields for mongoengine-fields."""
    
    def generate(self, field_name, field):
        """Tries to lookup a matching formfield generator (lowercase 
        field-classname) and raises a NotImplementedError of no generator
        can be found.
        """
        if hasattr(self, 'generate_%s' % field.__class__.__name__.lower()):
            return getattr(self, 'generate_%s' % \
                field.__class__.__name__.lower())(field_name, field)
        else:
            raise NotImplementedError('%s is not supported by MongoForm' % \
                field.__class__.__name__)

    def generate_stringfield(self, field_name, field):
        if field.regex:
            return forms.CharField(
                regex=field.regex,
                required=field.required,
                min_length=field.min_length,
                max_length=field.max_length,
                initial=field.default
            )
        elif field.choices:
            return forms.ChoiceField(
                required=field.required,
                initial=field.default,
                choices=zip(field.choices, field.choices)
            )
        elif field.max_length is None:
            return forms.CharField(
                required=field.required,
                initial=field.default,
                min_length=field.min_length,
                widget=forms.Textarea
            )
        else:
            return forms.CharField(
                required=field.required,
                min_length=field.min_length,
                max_length=field.max_length,
                initial=field.default
            )

    def generate_emailfield(self, field_name, field):
        return forms.EmailField(
            required=field.required,
            min_length=field.min_length,
            max_length=field.max_length,
            initial=field.default
        )

    def generate_urlfield(self, field_name, field):
        return forms.URLField(
            required=field.required,
            min_length=field.min_length,
            max_length=field.max_length,
            initial=field.default
        )

    def generate_intfield(self, field_name, field):
        return forms.IntegerField(
            required=field.required,
            min_value=field.min_value,
            max_value=field.max_value,
            initial=field.default
        )

    def generate_floatfield(self, field_name, field):
        return forms.FloatField(
            required=field.required,
            min_value=field.min_value,
            max_value=field.max_value,
            initial=field.default
        )

    def generate_decimalfield(self, field_name, field):
        return forms.DecimalField(
            required=field.required,
            min_value=field.min_value,
            max_value=field.max_value,
            initial=field.default
        )

    def generate_booleanfield(self, field_name, field):
        return forms.BooleanField(
            required=field.required,
            initial=field.default
        )

    def generate_datetimefield(self, field_name, field):
        return forms.DateTimeField(
            required=field.required,
            initial=field.default
        )

    def generate_referencefield(self, field_name, field):
        return ReferenceField(field.document_type.objects)


    def generate_listfield(self, field_name, field):
        return ListField(inner_field=field.field, required=field.required, initial=field.default)


    def generate_dictfield(self, field_name, field):
        return DictField(required=field.required, initial=field.default)