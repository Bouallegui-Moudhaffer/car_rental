import re
from typing import Dict, List, Any
import datetime as _dt

class ValidationError(Exception):
    """Raised when the form data fails validation."""

    def __init__(self, errors: List[str]):
        super().__init__("; ".join(errors))
        self.errors = errors

class BookingForm:
    """Validate the *booking.html* POST payload.*"""

    _CAB_CHOICES = {"0", "1", "2"}
    _ROUTE_CHOICES = {"0", "1", "2", "3", "4"}
    _DATE_FMT = "%Y-%m-%d"  # Choose a strict ISO format (yyyy-mm-dd)
    _TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")  # HH:MM 24-hour
    _LOCATION_RE = re.compile(r"^[A-Za-z0-9 ,.-]{2,100}$")

    def __init__(self, raw: Dict[str, Any]):
        self._raw = {k: (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}
        self.cleaned_data: Dict[str, Any] = {}
        self._errors: List[str] = []

    # ------------- public API -------------
    def is_valid(self) -> bool:
        self._errors.clear(); self.cleaned_data.clear()
        self._validate_user(); self._validate_cab(); self._validate_dates(); self._validate_time()
        self._validate_route(); self._validate_location("pickupLocation", "Pick-up location")
        self._validate_location("dropoffLocation", "Drop-off location")
        return not self._errors

    @property
    def errors(self) -> List[str]:
        return list(self._errors)

    # ------------- field validators -------------
    def _validate_user(self):
        uid = self._require("userId", friendly="User ID");  
        if uid is None: return
        if not re.fullmatch(r"^[A-Za-z0-9_]{4,32}$", uid):
            self._errors.append("User ID must be 4-32 characters of letters, numbers, or underscores.")
            return
        self.cleaned_data["userId"] = uid

    def _validate_cab(self):
        cab = self._require("cab", friendly="Cab selection");  
        if cab is None: return
        if cab not in self._CAB_CHOICES:
            self._errors.append("Please select a valid cab type.")
            return
        self.cleaned_data["cab"] = int(cab)

    def _validate_dates(self):
        sd_raw = self._require("startDate", friendly="Start date");  
        ed_raw = self._require("endDate", friendly="End date")
        if None in (sd_raw, ed_raw): return
        try:
            sd = _dt.datetime.strptime(sd_raw, self._DATE_FMT).date()
            ed = _dt.datetime.strptime(ed_raw, self._DATE_FMT).date()
        except ValueError:
            self._errors.append("Dates must be in YYYY-MM-DD format.")
            return
        if ed < sd:
            self._errors.append("End date cannot be before start date.")
            return
        self.cleaned_data.update(startDate=str(sd), endDate=str(ed))

    def _validate_time(self):
        t = self._require("time", friendly="Pick-up time");  
        if t is None: return
        if not self._TIME_RE.fullmatch(t):
            self._errors.append("Time must be in 24-hour HH:MM format.")
            return
        self.cleaned_data["time"] = t

    def _validate_route(self):
        r = self._require("route", friendly="Route selection");  
        if r is None: return
        if r not in self._ROUTE_CHOICES:
            self._errors.append("Please select a valid cab route.")
            return
        self.cleaned_data["route"] = int(r)

    def _validate_location(self, key: str, friendly: str):
        loc = self._require(key, friendly=friendly);  
        if loc is None: return
        if not self._LOCATION_RE.fullmatch(loc):
            self._errors.append(f"{friendly} contains invalid characters or is too long.")
            return
        self.cleaned_data[key] = loc

    # ------------- helper -------------
    def _require(self, key: str, *, friendly: str):
        value = self._raw.get(key)
        if value is None or (isinstance(value, str) and not value):
            self._errors.append(f"{friendly} is required.")
            return None
        return value


# ---------------------------------------------------------------------------
# Convenience wrappers -------------------------------------------------------
# ---------------------------------------------------------------------------

def validate_registration_form(form_data: Dict[str, Any]):
    form = RegistrationForm(form_data)
    ok = form.is_valid()
    return ok, (form.cleaned_data if ok else form.errors)

def validate_booking_form(form_data: Dict[str, Any]):
    form = BookingForm(form_data)
    ok = form.is_valid()
    return ok, (form.cleaned_data if ok else form.errors)