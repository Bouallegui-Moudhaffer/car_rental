import re
from typing import Any, Dict, List


class ResetPasswordForm:
    """Validation for *resetpassword.html* POST submission.*"""

    _USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,32}$")
    _SQUESTION_CHOICES = {"1", "2", "3", "4"}
    _PASSWORD_POLICY_RE = re.compile(
        r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()\-_=+{};:,<.>]).{8,64}$"
    )

    def __init__(self, raw: Dict[str, Any]):
        self._raw = {k: (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}
        self.cleaned_data: Dict[str, Any] = {}
        self._errors: List[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def is_valid(self) -> bool:
        self._errors.clear(); self.cleaned_data.clear()
        self._validate_username(); self._validate_squestion(); self._validate_answer(); self._validate_password()
        return not self._errors

    @property
    def errors(self) -> List[str]:
        return list(self._errors)

    # ------------------------------------------------------------------
    # Field validators
    # ------------------------------------------------------------------
    def _validate_username(self):
        value = self._require("username", friendly="Username")
        if value is None: return
        if not self._USERNAME_RE.fullmatch(value):
            self._errors.append("Username must be 4–32 characters of letters, numbers, or underscores.")
            return
        self.cleaned_data["username"] = value

    def _validate_squestion(self):
        val = self._require("squestion", friendly="Security question")
        if val is None: return
        if val not in self._SQUESTION_CHOICES:
            self._errors.append("Please select a valid security question.")
            return
        self.cleaned_data["squestion"] = int(val)

    def _validate_answer(self):
        ans = self._require("answer", friendly="Security answer")
        if ans is None: return
        if len(ans) > 64:
            self._errors.append("Security answer must be 64 characters or fewer.")
            return
        self.cleaned_data["answer"] = ans

    def _validate_password(self):
        pwd = self._require("password", friendly="New password")
        if pwd is None: return
        # Note: confirm password field in HTML lacks *name* attribute; cannot validate match here.
        if not self._PASSWORD_POLICY_RE.fullmatch(pwd):
            self._errors.append(
                "Password must be 8-64 chars and include upper & lower-case, a digit, and a special char."
            )
            return
        self.cleaned_data["password"] = pwd

    # ------------------------------------------------------------------
    # Helper
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

def validate_reset_form(form_data: Dict[str, Any]):
    form = ResetPasswordForm(form_data)
    ok = form.is_valid()
    return ok, (form.cleaned_data if ok else form.errors)
