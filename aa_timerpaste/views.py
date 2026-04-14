from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import ListView

from .forms import TimerPasteForm
from .models import SolarSystemMap, TimerEntry
from .parser import parse_many


class TimerEntryListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "aa_timerpaste.view_timerentry"
    model = TimerEntry
    template_name = "aa_timerpaste/list.html"
    context_object_name = "entries"
    paginate_by = 100


class TimerPasteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "aa_timerpaste.use_paste_import"
    template_name = "aa_timerpaste/paste.html"

    def get(self, request):
        form = TimerPasteForm()
        return render(request, self.template_name, {"form": form, "preview_rows": None})

    def post(self, request):
        form = TimerPasteForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "preview_rows": None})

        raw_text = form.cleaned_data["raw_text"]
        save_unknown_systems = form.cleaned_data["save_unknown_systems"]
        parsed = parse_many(raw_text)

        if "save" in request.POST:
            created = 0
            for row in parsed:
                region_name = ""
                if row.system_name:
                    mapping = SolarSystemMap.objects.filter(system_name__iexact=row.system_name).first()
                    if mapping:
                        region_name = mapping.region_name
                    else:
                        row.parse_status = "unknown_system"
                        row.parse_notes.append("System not found in local SDE map.")
                if row.parse_status == "unknown_system" and not save_unknown_systems:
                    continue

                TimerEntry.objects.create(
                    raw_text=row.raw_text,
                    details=row.details[:255],
                    objective=row.objective,
                    system_name=row.system_name,
                    region_name=region_name,
                    moon_or_location=row.moon_or_location[:128],
                    structure_type=row.structure_type,
                    owner_name=row.owner_name[:128],
                    distance_text=row.distance_text[:64],
                    timer_at=row.timer_at,
                    parse_status=row.parse_status,
                    parse_notes="; ".join(row.parse_notes),
                    created_by=request.user,
                )
                created += 1

            messages.success(request, f"Created {created} timer entries.")
            return redirect("aa_timerpaste:list")

        preview_rows = []
        for row in parsed:
            region_name = ""
            if row.system_name:
                mapping = SolarSystemMap.objects.filter(system_name__iexact=row.system_name).first()
                if mapping:
                    region_name = mapping.region_name
                else:
                    if row.parse_status == "parsed":
                        row.parse_status = "unknown_system"
                        row.parse_notes.append("System not found in local SDE map.")
            preview_rows.append((row, region_name))

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "preview_rows": preview_rows,
                "raw_text": raw_text,
                "save_unknown_systems": save_unknown_systems,
            },
        )
