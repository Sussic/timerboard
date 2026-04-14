from django import forms

from .models import TimerEntry


class TimerPasteForm(forms.Form):
    raw_text = forms.CharField(
        label="Paste timer text",
        widget=forms.Textarea(attrs={
            "rows": 18,
            "class": "form-control",
            "placeholder": "Paste Discord or clipboard timers here",
        }),
    )
    save_unknown_systems = forms.BooleanField(required=False, initial=True)
    save_duplicates = forms.BooleanField(required=False, initial=False)


class TimerEntryForm(forms.ModelForm):
    timer_at = forms.DateTimeField(
        input_formats=["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"],
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "YYYY-MM-DD HH:MM:SS"}),
    )

    class Meta:
        model = TimerEntry
        fields = [
            "details",
            "objective",
            "priority",
            "timer_state",
            "campaign_name",
            "system_name",
            "region_name",
            "constellation_name",
            "moon_or_location",
            "structure_type",
            "owner_name",
            "timer_at",
            "notes",
            "parse_notes",
            "is_archived",
        ]
        widgets = {
            "details": forms.TextInput(attrs={"class": "form-control"}),
            "objective": forms.Select(attrs={"class": "form-control"}),
            "priority": forms.Select(attrs={"class": "form-control"}),
            "timer_state": forms.Select(attrs={"class": "form-control"}),
            "campaign_name": forms.TextInput(attrs={"class": "form-control"}),
            "system_name": forms.TextInput(attrs={"class": "form-control"}),
            "region_name": forms.TextInput(attrs={"class": "form-control"}),
            "constellation_name": forms.TextInput(attrs={"class": "form-control"}),
            "moon_or_location": forms.TextInput(attrs={"class": "form-control"}),
            "structure_type": forms.Select(attrs={"class": "form-control"}),
            "owner_name": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "parse_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "is_archived": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class TimerFilterForm(forms.Form):
    q = forms.CharField(required=False)
    objective = forms.ChoiceField(required=False, choices=[("", "All objectives")] + TimerEntry.OBJECTIVE_CHOICES)
    structure_type = forms.ChoiceField(required=False, choices=[("", "All structures")] + TimerEntry.STRUCTURE_CHOICES)
    priority = forms.ChoiceField(required=False, choices=[("", "All priorities")] + TimerEntry.PRIORITY_CHOICES)
    timer_state = forms.ChoiceField(required=False, choices=[("", "All states")] + TimerEntry.STATE_CHOICES)
    region_name = forms.CharField(required=False)
    campaign_name = forms.CharField(required=False)
    include_archived = forms.BooleanField(required=False)
    upcoming_only = forms.BooleanField(required=False, initial=True)
