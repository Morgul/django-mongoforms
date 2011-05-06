import uuid
from django import forms
from django.template.loader import render_to_string
from django.utils.encoding import smart_unicode
from pymongo.errors import InvalidId
from pymongo.objectid import ObjectId
import simplejson as json


LISTFIELD_ITEM_LABEL = "listfield-items"
DICTFIELD_ITEM_LABEL = "dictfield-item"
DICTFIELD_ITEM_LABEL_VALUE_SUFFIX = "-value"

class DictWidget(forms.Widget):

    def __init__(self, show_all_fields=False, choices=None, keys={}, fields=[], *aargs, **kwaargs):
        self.show_all_fields, self.fields, self.keys, self.choices = show_all_fields,fields, keys, choices
        forms.Widget.__init__(self, *aargs, **kwaargs)

    def render(self, name, value, attrs=None):
        context = {}
        context['field_name'] = name
        context['field_uuid'] = uuid.uuid4()
        context['keys'] = json.dumps(self.keys)
        context['fields'] = json.dumps(self.fields)
        context['items'] = value
        context['choices'] = json.dumps(self.choices)
        context['show_all_fields'] = json.dumps(self.show_all_fields)
        return render_to_string('dict_mongofield.html', context)




class DictField(forms.Field):
    """
    Field for DictField.
    """

    def __init__(self, show_all_fields=False, choices=None,  keys={}, fields=[], widget=None, *aargs, **kwaargs):
        if widget is None:
            widget = DictWidget(show_all_fields=show_all_fields, choices=choices, keys=keys, fields=fields)
        self.show_all_fields, self.keys, self.fields = show_all_fields, keys, fields
        forms.Field.__init__(self, widget=widget, *aargs, **kwaargs)

    def save_data_to_model(self, model_instance, field_name, value):
        d = getattr(model_instance, field_name)
        if len(self.fields)>0:
            for key in value.keys():
                if key not in self.fields:
                    del value[key]
        d.update(value)

    def clean(self, value):
        value = json.loads(value)
        return value


    def prepare_value(self, value):
        if isinstance(value, str) or isinstance(value, unicode):
            return value
        if value is None:
            return json.dumps({})
        return json.dumps(value)


class ListWidget(forms.Widget):
    def __init__(self, get_choices, *args, **kwargs):
        self.get_choices = get_choices
        forms.Widget.__init__(self, *args, **kwargs)
    def render(self, name, value, attrs=None):
        context = {}
        context['selected'] = value
        context['field_uuid'] = uuid.uuid4()
        context['choices'] = json.dumps(dict(self.get_choices()))
        context['field_name'] = name
        return  render_to_string('list_mongofield.html', context)


class ListField(forms.Field):
    """
    Field for ListField.
    """

    def __init__(self, inner_field, *aargs, **kwaargs):
        self.__inner_field = MongoFormFieldGenerator().generate("somename", inner_field)
        try:
            get_choices = self.__inner_field._get_choices
        except AttributeError:
            get_choices =  lambda : []
        forms.Field.__init__(self, widget=ListWidget(get_choices=get_choices), *aargs, **kwaargs)


    def prepare_value(self, value):
        if isinstance(value, str) or isinstance(value, unicode):
            return value
        try:
            return json.dumps([self.__inner_field.prepare_value(v) for v in value])
        except TypeError:
            return json.dumps([])
    def clean(self, value):
        value = json.loads(value)
        if value is not None:
            res = [self.__inner_field.clean(v) for v in value]
            return res
        else:
            return []

class ReferenceField(forms.ChoiceField):
    """
    Reference field for mongo forms. Inspired by `django.forms.models.ModelChoiceField`.
    """
    def __init__(self, document, *aargs, **kwaargs):
        forms.Field.__init__(self, *aargs, **kwaargs)
        self.document = document

    def _get_document(self):
        return self._document

    def _set_document(self, document):
        self._document = document
        self.widget.choices = self.choices

    document = property(_get_document, _set_document)

    def _get_choices(self):
        #if hasattr(self, '_choices'):
        #    return self._choices
        x = self.document.objects.all()
        self._choices = [(smart_unicode(obj.id), smart_unicode(obj)) for obj in self.document.objects.all()]
        return self._choices

    choices = property(_get_choices, forms.ChoiceField._set_choices)

    def clean(self, value):
        try:
            oid = ObjectId(value)
            oid = super(ReferenceField, self).clean(oid)
            obj = self.document.objects.get(id=oid)

        except (TypeError, InvalidId, self.document.DoesNotExist):
            raise forms.ValidationError(self.error_messages['invalid_choice'] % {'value':value})
        return obj

    def prepare_value(self, value):
        self.choices = self.choices
        try:
            val = str(value.pk)
        except AttributeError:
            val = str(value)
        return super(ReferenceField, self).prepare_value(val)

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
        return ReferenceField(field.document_type)


    def generate_listfield(self, field_name, field):
        return ListField(inner_field=field.field, required=field.required, initial=field.default)


    def generate_dictfield(self, field_name, field):
        return DictField(required=field.required, initial=field.default)

    def generate_embeddeddocumentfield(self, field_name, field):
        #fixme
        return DictField(required=field.required, initial=field.default)