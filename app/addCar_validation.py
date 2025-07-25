import re
from typing import Any, Dict, List


class CarForm:
    """Validate *addcar.html* POST data for adding a new vehicle.*"""

    _CARID_RE = re.compile(r"^[A-Za-z0-9_-]{1,16}$")
    _MODEL_RE = re.compile(r"^[A-Za-z0-9 ]{2,50}$")
    _REG_RE = re.compile(r"^[A-Za-z0-9-]{4,20}$")
    _TYPE_CHOICES = {"0", "1", "2"}  # 0=Sedan,1=Hatchback,2=SUV

    def __init__(self, raw: Dict[str, Any]):
        self._raw = {k: (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}
        self.cleaned_data: Dict[str, Any] = {}
        self._errors: List[str] = []

    # ------------------------------------------------------------------
    def is_valid(self) -> bool:
        self._errors.clear(); self.cleaned_data.clear()
        self._validate_carid(); self._validate_model(); self._validate_registration()
        self._validate_seating(); self._validate_type(); self._validate_price()
        return not self._errors

    @property
    def errors(self) -> List[str]:
        return list(self._errors)

    # ------------------------------------------------------------------ field validators
    def _validate_carid(self):
        cid = self._require("carid", friendly="Car ID");  
        if cid is None: return
        if not self._CARID_RE.fullmatch(cid):
            self._errors.append("Car ID can contain A–Z, 0–9, dash, underscore (max 16 chars).")
            return
        self.cleaned_data["carid"] = cid

    def _validate_model(self):
        mdl = self._require("model", friendly="Model");  
        if mdl is None: return
        if not self._MODEL_RE.fullmatch(mdl):
            self._errors.append("Model name must be 2–50 letters/numbers/spaces.")
            return
        self.cleaned_data["model"] = mdl.title()

    def _validate_registration(self):
        reg = self._require("registration", friendly="Registration number");  
        if reg is None: return
        if not self._REG_RE.fullmatch(reg):
            self._errors.append("Registration number must be 4–20 letters/numbers/dashes.")
            return
        self.cleaned_data["registration"] = reg.upper()

    def _validate_seating(self):
        seat = self._require("seating", friendly="Seating capacity");  
        if seat is None: return
        try:
            seat_i = int(seat)
        except ValueError:
            self._errors.append("Seating capacity must be a number."); return
        if not 2 <= seat_i <= 6:
            self._errors.append("Seating capacity must be between 2 and 6."); return
        self.cleaned_data["seating"] = seat_i

    def _validate_type(self):
        t = self._require("type", friendly="Car type");  
        if t is None: return
        if t not in self._TYPE_CHOICES:
            self._errors.append("Please select a valid car type."); return
        self.cleaned_data["type"] = int(t)

    def _validate_price(self):
        p = self._require("price", friendly="Price per KM");  
        if p is None: return
        try:
            price_i = int(p)
        except ValueError:
            self._errors.append("Price per KM must be a number."); return
        if not 1 <= price_i <= 1000:
            self._errors.append("Price per KM must be between 1 and 1000."); return
        self.cleaned_data["price"] = price_i

    # ------------------------------------------------------------------ helper
    def _require(self, key: str, *, friendly: str):
        val = self._raw.get(key)
        if val is None or (isinstance(val, str) and not val):
            self._errors.append(f"{friendly} is required.")
            return None
        return val


# Wrapper

def validate_car_form(data: Dict[str, Any]):
    form = CarForm(data)
    ok = form.is_valid()
    return ok, (form.cleaned_data if ok else form.errors)
