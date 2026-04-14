from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import ListView

from .forms import TimerPasteForm
from .models import SolarSystemMap, TimerEntry
from .parser import parse_many


STRUCTURE_VALUES = [choice[0] for choice in TimerEntry.STRUCTURE_CHOICES]
OBJECTIVE_VALUES = [choice[0] for choice in TimerEntry.OBJECTIVE_CHOICES]


class TimerEntryListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "aa_timerpaste.view_timerentry"
    model = TimerEntry
    template_name = "aa_timerpaste/list.html"
    context_object_name = "entries"
    paginate_by = 200


class TimerPasteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "aa_timerpaste.use_paste_import"
    template_name = "aa_timerpaste/paste.html"

    def _region_for_system(self, system_name: str) -> str:
        if not system_name:
            return ""
        mapping = SolarSystemMap.objects.filter(system_name__iexact=system_name).first()
        return mapping.region_name if mapping else ""

    def get(self, request):
        form = TimerPasteForm()
        return render(request, self.template_name, {
            "form": form,
            "preview_rows": None,
            "structure_choices": TimerEntry.STRUCTURE_CHOICES,
            "objective_choices": TimerEntry.OBJECTIVE_CHOICES,
        })

    def post(self, request):
        raw_text = request.POST.get("raw_text", "")
        form = TimerPasteForm({"raw_text": raw_text, "save_unknown_systems": request.POST.get("save_unknown_systems")})
        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form,
                "preview_rows": None,
                "structure_choices": TimerEntry.STRUCTURE_CHOICES,
                "objective_choices": TimerEntry.OBJECTIVE_CHOICES,
            })

        if "save" in request.POST:
            rows = self._rows_from_post(request)
            save_unknown_systems = bool(request.POST.get("save_unknown_systems"))
            created = 0
            for row in rows:
                region_name = self._region_for_system(row["system_name"])
                if not region_name and row["system_name"]:
                    row["parse_notes"] = self._append_note(row["parse_notes"], "System not found in local SDE map.")
                row["region_name"] = region_name
                if not row["system_name"] and not save_unknown_systems:
                    continue
                TimerEntry.objects.create(
                    raw_text=row["raw_text"],
                    details=row["details"][:255],
                    objective=row["objective"],
                    system_name=row["system_name"],
                    region_name=row["region_name"],
                    moon_or_location=row["moon_or_location"][:128],
                    structure_type=row["structure_type"],
                    owner_name=row["owner_name"][:128],
                    timer_at=row["timer_at"],
                    parse_notes=row["parse_notes"],
                    created_by=request.user,
                )
                created += 1
            messages.success(request, f"Created {created} timer entries.")
            return redirect("aa_timerpaste:list")

        preview_rows = self._build_preview_rows(raw_text)
        return render(request, self.template_name, {
            "form": form,
            "preview_rows": preview_rows,
            "structure_choices": TimerEntry.STRUCTURE_CHOICES,
            "objective_choices": TimerEntry.OBJECTIVE_CHOICES,
        })

    def _append_note(self, notes: str, extra: str) -> str:
        notes = notes.strip()
        return f"{notes}; {extra}" if notes else extra

    def _build_preview_rows(self, raw_text: str):
        rows = []
        for idx, parsed in enumerate(parse_many(raw_text)):
            region_name = self._region_for_system(parsed.system_name)
            notes = "; ".join(parsed.parse_notes)
            if parsed.system_name and not region_name:
                notes = self._append_note(notes, "System not found in local SDE map.")
            rows.append({
                "idx": idx,
                "keep": True,
                "raw_text": parsed.raw_text,
                "details": parsed.details,
                "objective": parsed.objective if parsed.objective in OBJECTIVE_VALUES else "hostile",
                "system_name": parsed.system_name,
                "region_name": region_name,
                "moon_or_location": parsed.moon_or_location,
                "structure_type": parsed.structure_type if parsed.structure_type in STRUCTURE_VALUES else "other",
                "owner_name": parsed.owner_name,
                "timer_at": parsed.timer_at.strftime("%Y-%m-%d %H:%M:%S"),
                "parse_notes": notes,
            })
        return rows

    def _rows_from_post(self, request):
        rows = []
        count = int(request.POST.get("row_count", "0") or "0")
        for idx in range(count):
            if not request.POST.get(f"keep_{idx}"):
                continue
            rows.append({
                "raw_text": request.POST.get(f"raw_text_{idx}", ""),
                "details": request.POST.get(f"details_{idx}", "").strip(),
                "objective": request.POST.get(f"objective_{idx}", "hostile"),
                "system_name": request.POST.get(f"system_name_{idx}", "").strip(),
                "moon_or_location": request.POST.get(f"moon_or_location_{idx}", "").strip(),
                "structure_type": request.POST.get(f"structure_type_{idx}", "other"),
                "owner_name": request.POST.get(f"owner_name_{idx}", "").strip(),
                "timer_at": request.POST.get(f"timer_at_{idx}", "").strip(),
                "parse_notes": request.POST.get(f"parse_notes_{idx}", "").strip(),
            })
        from datetime import datetime, timezone
        for row in rows:
            row["timer_at"] = datetime.strptime(row["timer_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            if row["objective"] not in OBJECTIVE_VALUES:
                row["objective"] = "hostile"
            if row["structure_type"] not in STRUCTURE_VALUES:
                row["structure_type"] = "other"
        return rows
