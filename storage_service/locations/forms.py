
from django import forms
import django.utils
import django.core.exceptions

from locations import models


# CUSTOM WIDGETS
# Move this to a widgets.py file if there are more than a couple

class DisableableSelectWidget(forms.Select):
    """
    Modification of Select widget to allow specific choices to be disabled.

    Set disabled_choices to the values of the choices that should be disabled.
    Custom clean methods should also be added to ensure those values cannot be
    chosen.

    Example:
    def __init__(self, *args, **kwargs):
        super(ThisForm, self).__init__(*args, **kwargs)
        self.fields['choicesfield'].widget.disabled_choices = (value1, value2)
    """
    # From https://djangosnippets.org/snippets/2743/
    # Updated for Django 1.5 Select widget
    def __init__(self, attrs=None, disabled_choices=(), choices=()):
        super(DisableableSelectWidget, self).__init__(attrs, choices)
        self.disabled_choices = list(disabled_choices)

    def render_option(self, selected_choices, option_value, option_label):
        option_value = django.utils.encoding.force_text(option_value)
        if option_value in selected_choices:
            selected_html = django.utils.safestring.mark_safe(' selected="selected"')
            if not self.allow_multiple_selected:
                # Only allow for a single selection.
                selected_choices.remove(option_value)
        else:
            selected_html = ''
        if option_value in self.disabled_choices:
            disabled_html = django.utils.safestring.mark_safe(' disabled="disabled"')
        else:
            disabled_html = ''
        return django.utils.html.format_html(
            '<option value="{0}"{1}{2}>{3}</option>',
            option_value,
            selected_html,
            disabled_html,
            django.utils.encoding.force_text(option_label)
        )


# FORMS

class PipelineForm(forms.ModelForm):
    create_default_locations = forms.BooleanField(required=False,
        initial=True,
        label="Default Locations:",
        help_text="Enabled if default locations should be created for this pipeline")

    class Meta:
        model = models.Pipeline
        fields = ('uuid', 'description', 'remote_name', 'api_username', 'api_key', 'enabled')


class SpaceForm(forms.ModelForm):
    class Meta:
        model = models.Space
        fields = ('access_protocol', 'size', 'path', 'staging_path')

    def __init__(self, *args, **kwargs):
        super(SpaceForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.uuid:
            # If editing (not creating a new object) access protocol shouldn't
            # be changed.  Remove from fields, print in template
            del self.fields['access_protocol']

    def clean_access_protocol(self):
        instance = getattr(self, 'instance', None)
        if instance and instance.uuid:
            return instance.access_protocol
        else:
            return self.cleaned_data['access_protocol']


class DuracloudForm(forms.ModelForm):
    class Meta:
        model = models.Duracloud
        fields = ('host', 'user', 'password', 'duraspace')


class LocalFilesystemForm(forms.ModelForm):
    class Meta:
        model = models.LocalFilesystem
        fields = ()


class NFSForm(forms.ModelForm):
    class Meta:
        model = models.NFS
        fields = ('remote_name', 'remote_path', 'version', 'manually_mounted')


class PipelineLocalFSForm(forms.ModelForm):
    # TODO SpaceForm.path help text should say path to space on local machine
    class Meta:
        model = models.PipelineLocalFS
        fields = ('remote_user', 'remote_name', )


class LockssomaticForm(forms.ModelForm):
    # TODO SpaceForm.path help text should say path to staging space, preferably local
    class Meta:
        model = models.Lockssomatic
        fields = ('sd_iri', 'content_provider_id', 'external_domain', 'keep_local')

    def clean_external_domain(self):
        data = self.cleaned_data['external_domain']
        data = data.rstrip('/')
        return data


class FedoraForm(forms.ModelForm):
    class Meta:
        model = models.Fedora
        fields = ('fedora_user', 'fedora_password', 'fedora_name', )


class LocationForm(forms.ModelForm):
    class Meta:
        model = models.Location
        fields = ('purpose', 'pipeline', 'relative_path', 'description', 'quota', 'enabled')
        widgets = {
            'purpose': DisableableSelectWidget(),
        }

    def __init__(self, *args, **kwargs):
        """
        Should be passed parameter 'space_protocol' which is the entry from
        Space.ACCESS_PROTOCOL_CHOICES that this Location belongs to.
        """
        space_protocol = kwargs.get('space_protocol')
        del kwargs['space_protocol']
        super(LocationForm, self).__init__(*args, **kwargs)
        # Disable purposes that aren't in the Space's whitelist
        all_ = set(x[0] for x in models.Location.PURPOSE_CHOICES)
        if space_protocol in [x[0] for x in models.Space.ACCESS_PROTOCOL_CHOICES]:
            from constants import PROTOCOL
            self.whitelist = PROTOCOL[space_protocol]['model'].ALLOWED_LOCATION_PURPOSE
        else:
            self.whitelist = all_
        blacklist = all_ - set(self.whitelist)
        self.fields['purpose'].widget.disabled_choices = blacklist

    def clean_purpose(self):
        # Server-side enforcement of what Location purposes are allowed
        data = self.cleaned_data['purpose']
        if data not in self.whitelist:
            raise django.core.exceptions.ValidationError('Invalid purpose')
        return data


class ConfirmEventForm(forms.ModelForm):
    class Meta:
        model = models.Event
        fields = ('status_reason',)

    def __init__(self, *args, **kwargs):
        super(ConfirmEventForm, self).__init__(*args, **kwargs)
        self.fields['status_reason'].required = True

class CallbackForm(forms.ModelForm):
    class Meta:
        model = models.Callback
        fields = ('uri', 'event', 'method', 'expected_status')
