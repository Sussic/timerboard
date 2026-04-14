from django import forms


class TimerPasteForm(forms.Form):
    raw_text = forms.CharField(
        label="Paste timer text",
        widget=forms.Textarea(attrs={"rows": 18, "class": "form-control", "placeholder": "Paste Discord or clipboard timers here"}),
    )
    save_unknown_systems = forms.BooleanField(required=False, initial=True)
