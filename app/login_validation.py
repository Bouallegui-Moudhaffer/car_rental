import re
from typing import Any, Dict, List


class LoginForm:
    """Server‑side validation for *signin.html*.

    Fields expected (POST):
        * **Username** – 4‑32 chars, letters/numbers/underscore.
        * **Password** – 8‑64 chars (any printable characters).

    Example
    -------
    >>> form = LoginForm(request.form)
    >>> if form.is_valid():
    ...     user = form.cleaned_data["username"]
    ...     pwd  = form.cleaned_data["password"]
    """

    _USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,32}$")

    def __init__(self, raw_data: Dict[str, Any]):
        # Normalise: trim whitespace for str values
        self._raw = {
            k: (v.strip() if isinstance(v, str) else v) for k, v in raw_data.items()
        }
        self.cleaned_data: Dict[str, Any] = {}
        self._errors: List[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def is_valid(self) -> bool:
        """Run all checks and return `True` on success."""
        self._errors.clear()
        self.cleaned_data.clear()

        self._validate_username()
        self._validate_password()

        return not self._errors

    @property
    def errors(self) -> List[str]:
        """Return collected error messages (after `is_valid()`)."""
        return list(self._errors)

    # ------------------------------------------------------------------
    # Field validators
    # ------------------------------------------------------------------
    def _validate_username(self) -> None:
        value = self._require("Username", friendly="Username")
        if value is None:
            return
        if not self._USERNAME_RE.fullmatch(value):
            self._errors.append(
                "Username must be 4–32 characters long “A–Z a–z 0–9 _”."
            )
            return
        self.cleaned_data["username"] = value

    def _validate_password(self) -> None:
        value = self._require("Password", friendly="Password")
        if value is None:
            return
        if not (8 <= len(value) <= 64):
            self._errors.append("Password must be between 8 and 64 characters long.")
            return
        self.cleaned_data["password"] = value

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

def validate_login_form(form_data: Dict[str, Any]):
    """Return (ok, data_or_errors)."""
    form = LoginForm(form_data)
    ok = form.is_valid()
    return ok, (form.cleaned_data if ok else form.errors)
