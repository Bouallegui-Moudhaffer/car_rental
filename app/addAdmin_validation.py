import re
from typing import Any, Dict, List


class AdminRegistrationForm:
    """Validation for addadmin.html POST data."""

    _NAME_RE = re.compile(r"^[A-Za-z]+$")
    _USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,32}$")
    _EMAIL_RE = re.compile(r"^[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9-.]+$")
    _PHONE_RE = re.compile(r"^[0-9]{10}$")
    _PASSWORD_POLICY_RE = re.compile(
        r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()\-_=+{};:,<.>]).{8,64}$"
    )
    _SQUESTION_CHOICES = {"1", "2", "3", "4"}

    def __init__(self, raw: Dict[str, Any]):
        self._raw = {k: (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}
        self.cleaned_data: Dict[str, Any] = {}
        self._errors: List[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def is_valid(self) -> bool:
        self._errors.clear(); self.cleaned_data.clear()
        self._validate_name("FName", friendly="First name")
        self._validate_name("lName", friendly="Last name")
        self._validate_username(); self._validate_email(); self._validate_phone()
        self._validate_age(); self._validate_passwords(); self._validate_security(); self._validate_answer()
        return not self._errors

    @property
    def errors(self) -> List[str]:
        return list(self._errors)

    # ------------------------------------------------------------------
    # Field validators
    # ------------------------------------------------------------------
    def _validate_name(self, key: str, *, friendly: str):
        value = self._require(key, friendly=friendly)
        if value is None: return
        if not self._NAME_RE.fullmatch(value):
            self._errors.append(f"{friendly} must contain letters only (A–Z).")
            return
        self.cleaned_data[key] = value.capitalize()

    def _validate_username(self):
        value = self._require("username", friendly="Username");  
        if value is None: return
        if not self._USERNAME_RE.fullmatch(value):
            self._errors.append("Username must be 4–32 characters of letters, numbers, or underscores.")
            return
        self.cleaned_data["username"] = value

    def _validate_email(self):
        value = self._require("email", friendly="Email");  
        if value is None: return
        if not self._EMAIL_RE.fullmatch(value):
            self._errors.append("Please enter a valid e-mail address.")
            return
        self.cleaned_data["email"] = value.lower()

    def _validate_phone(self):
        value = self._require("PhoneNumber", friendly="Phone number");  
        if value is None: return
        if not self._PHONE_RE.fullmatch(value):
            self._errors.append("Phone number must be exactly 10 digits.")
            return
        self.cleaned_data["phone"] = value

    def _validate_age(self):
        value = self._require("age", friendly="Age");  
        if value is None: return
        try:
            age_int = int(value)
        except ValueError:
            self._errors.append("Age must be a number."); return
        if age_int < 15:
            self._errors.append("Admin must be at least 15 years old.")
        elif age_int > 120:
            self._errors.append("Age seems unrealistic; please enter a valid age.")
        else:
            self.cleaned_data["age"] = age_int

    def _validate_passwords(self):
        pwd = self._require("Password", friendly="Password"); conf = self._require("ConfirmPassword", friendly="Confirm password")
        if None in (pwd, conf): return
        if pwd != conf:
            self._errors.append("Password and confirmation do not match."); return
        if not self._PASSWORD_POLICY_RE.fullmatch(pwd):
            self._errors.append("Password must be 8-64 chars incl. upper, lower, digit & special char."); return
        self.cleaned_data["password"] = pwd

    def _validate_security(self):
        val = self._require("squestion", friendly="Security question");  
        if val is None: return
        if val not in self._SQUESTION_CHOICES:
            self._errors.append("Please select a valid security question."); return
        self.cleaned_data["squestion"] = int(val)

    def _validate_answer(self):
        ans = self._require("answer", friendly="Security answer");  
        if ans is None: return
        if len(ans) > 64:
            self._errors.append("Security answer must be ≤ 64 characters."); return
        self.cleaned_data["answer"] = ans

    # ------------------------------------------------------------------
    def _require(self, key: str, *, friendly: str):
        value = self._raw.get(key)
        if value is None or (isinstance(value, str) and not value):
            self._errors.append(f"{friendly} is required.")
            return None
        return value


# ----------------------------------------------------------------------
# Convenience wrapper
# ----------------------------------------------------------------------

def validate_admin_form(data: Dict[str, Any]):
    form = AdminRegistrationForm(data)
    ok = form.is_valid()
    return ok, (form.cleaned_data if ok else form.errors)
