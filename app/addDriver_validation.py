import re
from typing import Any, Dict, List


class DriverForm:
    """Validate adddriver.html POST data."""

    _NAME_RE = re.compile(r"^[A-Za-z]+$")
    _PHONE_RE = re.compile(r"^[0-9]{10}$")
    _LICENSE_RE = re.compile(r"^[A-Za-z0-9-]{5,20}$")

    def __init__(self, raw: Dict[str, Any]):
        self._raw = {k: (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}
        self.cleaned_data: Dict[str, Any] = {}
        self._errors: List[str] = []

    def is_valid(self) -> bool:
        self._errors.clear(); self.cleaned_data.clear()
        self._validate_name("dfname", "First name")
        self._validate_name("dlname", "Last name")
        self._validate_phone()
        self._validate_age()
        self._validate_license()
        return not self._errors

    @property
    def errors(self):
        return list(self._errors)

    # ------------------------------------------------------------------ field validators
    def _validate_name(self, key: str, friendly: str):
        v = self._require(key, friendly=friendly)
        if v is None: return
        if not self._NAME_RE.fullmatch(v):
            self._errors.append(f"{friendly} must contain letters only (A–Z).")
            return
        self.cleaned_data[key] = v.capitalize()

    def _validate_phone(self):
        p = self._require("dphone", friendly="Phone number")
        if p is None: return
        if not self._PHONE_RE.fullmatch(p):
            self._errors.append("Phone number must be exactly 10 digits.")
            return
        self.cleaned_data["dphone"] = p

    def _validate_age(self):
        a = self._require("dage", friendly="Age")
        if a is None: return
        try:
            age_i = int(a)
        except ValueError:
            self._errors.append("Age must be a number."); return
        if not 18 <= age_i <= 70:
            self._errors.append("Driver age must be between 18 and 70."); return
        self.cleaned_data["dage"] = age_i

    def _validate_license(self):
        lic = self._require("license", friendly="License number")
        if lic is None: return
        if not self._LICENSE_RE.fullmatch(lic):
            self._errors.append("License number must be 5–20 alphanumerics or dashes.")
            return
        self.cleaned_data["license"] = lic.upper()

    # helper
    def _require(self, key: str, *, friendly: str):
        val = self._raw.get(key)
        if val is None or (isinstance(val, str) and not val):
            self._errors.append(f"{friendly} is required.")
            return None
        return val


def validate_driver_form(data: Dict[str, Any]):
    form = DriverForm(data)
    ok = form.is_valid()
    return ok, (form.cleaned_data if ok else form.errors)
