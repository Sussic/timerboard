import csv
import json
from collections import Counter
from datetime import datetime, timezone

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone as dj_timezone
from django.views import View
from django.views.generic import ListView

from .forms import TimerEntryForm, TimerFilterForm, TimerPasteForm
from .models import SolarSystemMap, TimerEntry
from .parser import parse_many


STRUCTURE_VALUES = [choice[0] for choice in TimerEntry.STRUCTURE_CHOICES]
OBJECTIVE_VALUES = [choice[0] for choice in TimerEntry.OBJECTIVE_CHOICES]
PRIORITY_VALUES = [choice[0] for choice in TimerEntry.PRIORITY_CHOICES]
STATE_VALUES = [choice[0] for choice in TimerEntry.STATE_CHOICES]


class TimerQueryMixin:
    def filtered_queryset(self, request):
        qs = TimerEntry.objects.all()
        form = TimerFilterForm(request.GET or None)
        if form.is_valid():
            data = form.cleaned_data
            q = (data.get("q") or "").strip()
            if q:
                qs = qs.filter(
                    Q(details__icontains=q)
                    | Q(system_name__icontains=q)
                    | Q(region_name__icontains=q)
                    | Q(moon_or_location__icontains=q)
                    | Q(owner_name__icontains=q)
                    | Q(campaign_name__icontains=q)
                    | Q(notes__icontains=q)
                )
            if data.get("objective"):
                qs = qs.filter(objective=data["objective"])
            if data.get("structure_type"):
                qs = qs.filter(structure_type=data["structure_type"])
            if data.get("priority"):
                qs = qs.filter(priority=data["priority"])
            if data.get("timer_state"):
                qs = qs.filter(timer_state=data["timer_state"])
            if data.get("region_name"):
                qs = qs.filter(region_name__icontains=data["region_name"].strip())
            if data.get("campaign_name"):
                qs = qs.filter(campaign_name__icontains=data["campaign_name"].strip())
            if not data.get("include_archived"):
                qs = qs.filter(is_archived=False)
            if data.get("upcoming_only"):
                qs = qs.filter(timer_at__gte=dj_timezone.now())
        else:
            qs = qs.filter(is_archived=False, timer_at__gte=dj_timezone.now())
        return qs.order_by("timer_at", "priority", "region_name", "system_name"), form


class TimerEntryListView(LoginRequiredMixin, PermissionRequiredMixin, TimerQueryMixin, ListView):
    permission_required = "aa_timerpaste.view_timerentry"
    model = TimerEntry
    template_name = "aa_timerpaste/list.html"
    context_object_name = "entries"
    paginate_by = 250

    def get_queryset(self):
        qs, self.filter_form = self.filtered_queryset(self.request)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        context["board_stats"] = {
            "filtered_count": self.object_list.count(),
            "active_count": TimerEntry.objects.filter(is_archived=False).count(),
            "upcoming_count": TimerEntry.objects.filter(is_archived=False, timer_at__gte=dj_timezone.now()).count(),
            "archived_count": TimerEntry.objects.filter(is_archived=True).count(),
        }
        return context


class TimerPasteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "aa_timerpaste.use_paste_import"
    template_name = "aa_timerpaste/paste.html"

    def _lookup_map(self, system_name: str):
        if not system_name:
            return None
        return SolarSystemMap.objects.filter(system_name__iexact=system_name).first()

    def _region_for_system(self, system_name: str) -> str:
        mapping = self._lookup_map(system_name)
        return mapping.region_name if mapping else ""

    def _constellation_for_system(self, system_name: str) -> str:
        mapping = self._lookup_map(system_name)
        return mapping.constellation_name if mapping else ""

    def get(self, request):
        form = TimerPasteForm()
        return render(request, self.template_name, {
            "form": form,
            "preview_rows": None,
            "structure_choices": TimerEntry.STRUCTURE_CHOICES,
            "objective_choices": TimerEntry.OBJECTIVE_CHOICES,
            "priority_choices": TimerEntry.PRIORITY_CHOICES,
            "state_choices": TimerEntry.STATE_CHOICES,
        })

    def post(self, request):
        raw_text = request.POST.get("raw_text", "")
        form = TimerPasteForm({
            "raw_text": raw_text,
            "save_unknown_systems": request.POST.get("save_unknown_systems"),
            "save_duplicates": request.POST.get("save_duplicates"),
        })
        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form,
                "preview_rows": None,
                "structure_choices": TimerEntry.STRUCTURE_CHOICES,
                "objective_choices": TimerEntry.OBJECTIVE_CHOICES,
                "priority_choices": TimerEntry.PRIORITY_CHOICES,
                "state_choices": TimerEntry.STATE_CHOICES,
            })

        if "save" in request.POST:
            rows = self._rows_from_post(request)
            save_unknown_systems = bool(request.POST.get("save_unknown_systems"))
            save_duplicates = bool(request.POST.get("save_duplicates"))
            created = 0
            skipped = 0
            for row in rows:
                region_name = self._region_for_system(row["system_name"])
                constellation_name = self._constellation_for_system(row["system_name"])
                if not region_name and row["system_name"]:
                    row["parse_notes"] = self._append_note(row["parse_notes"], "System not found in local SDE map.")
                row["region_name"] = region_name
                row["constellation_name"] = constellation_name
                if not row["system_name"] and not save_unknown_systems:
                    skipped += 1
                    continue

                duplicate_key = self._duplicate_key(row)
                duplicate_exists = TimerEntry.objects.filter(duplicate_key=duplicate_key, is_archived=False).exists()
                if duplicate_exists and not save_duplicates:
                    skipped += 1
                    continue

                TimerEntry.objects.create(
                    raw_text=row["raw_text"],
                    details=row["details"][:255],
                    objective=row["objective"],
                    priority=row["priority"],
                    timer_state=row["timer_state"],
                    campaign_name=row["campaign_name"][:128],
                    system_name=row["system_name"],
                    region_name=row["region_name"],
                    constellation_name=row["constellation_name"],
                    moon_or_location=row["moon_or_location"][:128],
                    structure_type=row["structure_type"],
                    owner_name=row["owner_name"][:128],
                    timer_at=row["timer_at"],
                    notes=row["notes"],
                    parse_notes=row["parse_notes"],
                    source_kind="paste",
                    created_by=request.user,
                    updated_by=request.user,
                )
                created += 1
            if skipped:
                messages.warning(request, f"Created {created} timer entries. Skipped {skipped}.")
            else:
                messages.success(request, f"Created {created} timer entries.")
            return redirect("aa_timerpaste:list")

        preview_rows = self._build_preview_rows(raw_text)
        return render(request, self.template_name, {
            "form": form,
            "preview_rows": preview_rows,
            "structure_choices": TimerEntry.STRUCTURE_CHOICES,
            "objective_choices": TimerEntry.OBJECTIVE_CHOICES,
            "priority_choices": TimerEntry.PRIORITY_CHOICES,
            "state_choices": TimerEntry.STATE_CHOICES,
        })

    def _append_note(self, notes: str, extra: str) -> str:
        notes = notes.strip()
        return f"{notes}; {extra}" if notes else extra

    def _duplicate_key(self, row: dict) -> str:
        timer_part = row["timer_at"].strftime("%Y-%m-%d %H:%M:%S") if row.get("timer_at") else ""
        return "|".join([
            (row.get("system_name") or "").strip().upper(),
            (row.get("moon_or_location") or "").strip().upper(),
            (row.get("structure_type") or "").strip().lower(),
            timer_part,
        ])

    def _existing_duplicate_keys(self):
        return set(TimerEntry.objects.filter(is_archived=False).values_list("duplicate_key", flat=True))

    def _build_preview_rows(self, raw_text: str):
        parsed_rows = []
        existing_duplicate_keys = self._existing_duplicate_keys()
        block_counter = Counter()
        for idx, parsed in enumerate(parse_many(raw_text)):
            region_name = self._region_for_system(parsed.system_name)
            constellation_name = self._constellation_for_system(parsed.system_name)
            notes = "; ".join(parsed.parse_notes)
            timer_text = parsed.timer_at.strftime("%Y-%m-%d %H:%M:%S")
            row = {
                "idx": idx,
                "keep": True,
                "raw_text": parsed.raw_text,
                "details": parsed.details,
                "objective": parsed.objective if parsed.objective in OBJECTIVE_VALUES else "hostile",
                "priority": "normal",
                "timer_state": "unknown",
                "campaign_name": "",
                "system_name": parsed.system_name,
                "region_name": region_name,
                "constellation_name": constellation_name,
                "moon_or_location": parsed.moon_or_location,
                "structure_type": parsed.structure_type if parsed.structure_type in STRUCTURE_VALUES else "other",
                "owner_name": parsed.owner_name,
                "timer_at": timer_text,
                "notes": "",
                "parse_notes": notes,
                "duplicate_warning": "",
            }
            dup_key = "|".join([
                (row["system_name"] or "").strip().upper(),
                (row["moon_or_location"] or "").strip().upper(),
                (row["structure_type"] or "").strip().lower(),
                timer_text,
            ])
            block_counter[dup_key] += 1
            if row["system_name"] and not region_name:
                row["parse_notes"] = self._append_note(row["parse_notes"], "System not found in local SDE map.")
            if dup_key in existing_duplicate_keys:
                row["duplicate_warning"] = "Possible duplicate of an existing active timer."
            parsed_rows.append(row)

        for row in parsed_rows:
            dup_key = "|".join([
                (row["system_name"] or "").strip().upper(),
                (row["moon_or_location"] or "").strip().upper(),
                (row["structure_type"] or "").strip().lower(),
                row["timer_at"],
            ])
            if block_counter[dup_key] > 1:
                row["duplicate_warning"] = self._append_note(row["duplicate_warning"], "Duplicate within this import block.")
        return parsed_rows

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
                "priority": request.POST.get(f"priority_{idx}", "normal"),
                "timer_state": request.POST.get(f"timer_state_{idx}", "unknown"),
                "campaign_name": request.POST.get(f"campaign_name_{idx}", "").strip(),
                "system_name": request.POST.get(f"system_name_{idx}", "").strip(),
                "moon_or_location": request.POST.get(f"moon_or_location_{idx}", "").strip(),
                "structure_type": request.POST.get(f"structure_type_{idx}", "other"),
                "owner_name": request.POST.get(f"owner_name_{idx}", "").strip(),
                "timer_at": request.POST.get(f"timer_at_{idx}", "").strip(),
                "notes": request.POST.get(f"notes_{idx}", "").strip(),
                "parse_notes": request.POST.get(f"parse_notes_{idx}", "").strip(),
            })
        for row in rows:
            row["timer_at"] = datetime.strptime(row["timer_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            if row["objective"] not in OBJECTIVE_VALUES:
                row["objective"] = "hostile"
            if row["priority"] not in PRIORITY_VALUES:
                row["priority"] = "normal"
            if row["timer_state"] not in STATE_VALUES:
                row["timer_state"] = "unknown"
            if row["structure_type"] not in STRUCTURE_VALUES:
                row["structure_type"] = "other"
        return rows


class TimerEntryEditView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "aa_timerpaste.change_timerentry"
    template_name = "aa_timerpaste/edit.html"

    def get(self, request, pk):
        entry = get_object_or_404(TimerEntry, pk=pk)
        form = TimerEntryForm(instance=entry)
        return render(request, self.template_name, {"entry": entry, "form": form})

    def post(self, request, pk):
        entry = get_object_or_404(TimerEntry, pk=pk)
        form = TimerEntryForm(request.POST, instance=entry)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            obj.source_kind = "manual"
            obj.save()
            messages.success(request, "Timer updated.")
            return redirect("aa_timerpaste:list")
        return render(request, self.template_name, {"entry": entry, "form": form})


class TimerEntryArchiveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "aa_timerpaste.archive_timerentry"

    def post(self, request, pk):
        entry = get_object_or_404(TimerEntry, pk=pk)
        entry.is_archived = True
        entry.archived_at = dj_timezone.now()
        entry.archived_by = request.user
        entry.updated_by = request.user
        entry.save()
        messages.success(request, "Timer archived.")
        return redirect("aa_timerpaste:list")


class TimerEntryDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "aa_timerpaste.delete_timerentry"

    def post(self, request, pk):
        entry = get_object_or_404(TimerEntry, pk=pk)
        entry.delete()
        messages.success(request, "Timer deleted.")
        return redirect("aa_timerpaste:list")


class TimerExportCsvView(LoginRequiredMixin, PermissionRequiredMixin, TimerQueryMixin, View):
    permission_required = "aa_timerpaste.export_timerentry"

    def get(self, request):
        qs, _ = self.filtered_queryset(request)
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="timerboard.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "details", "objective", "priority", "state", "campaign", "system", "region",
            "constellation", "moon_or_location", "structure", "owner", "timer_at",
            "notes", "creator", "archived"
        ])
        for row in qs:
            writer.writerow([
                row.details, row.objective, row.priority, row.timer_state, row.campaign_name,
                row.system_name, row.region_name, row.constellation_name, row.moon_or_location,
                row.structure_type, row.owner_name, row.timer_at.isoformat(),
                row.notes, str(row.created_by or ""), row.is_archived,
            ])
        return response


class TimerExportJsonView(LoginRequiredMixin, PermissionRequiredMixin, TimerQueryMixin, View):
    permission_required = "aa_timerpaste.export_timerentry"

    def get(self, request):
        qs, _ = self.filtered_queryset(request)
        payload = []
        for row in qs:
            payload.append({
                "id": row.id,
                "details": row.details,
                "objective": row.objective,
                "priority": row.priority,
                "timer_state": row.timer_state,
                "campaign_name": row.campaign_name,
                "system_name": row.system_name,
                "region_name": row.region_name,
                "constellation_name": row.constellation_name,
                "moon_or_location": row.moon_or_location,
                "structure_type": row.structure_type,
                "owner_name": row.owner_name,
                "timer_at": row.timer_at.isoformat(),
                "notes": row.notes,
                "parse_notes": row.parse_notes,
                "created_by": str(row.created_by or ""),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                "is_archived": row.is_archived,
            })
        return JsonResponse(payload, safe=False)
