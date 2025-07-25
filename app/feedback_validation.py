import re
from typing import Any, Dict, List


class FeedbackForm:
    """Validate feedback.html POST payload."""

    _USER_RE = re.compile(r"^[A-Za-z0-9_]{4,32}$")
    _EMAIL_RE = re.compile(r"^[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9-.]+$")
    _RATING_CHOICES = {"0", "1", "2", "3"}  # excellent..poor

    def __init__(self, raw: Dict[str, Any]):
        self._raw = {k: (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}
        self.cleaned_data: Dict[str, Any] = {}
        self._errors: List[str] = []

    def is_valid(self) -> bool:
        self._errors.clear(); self.cleaned_data.clear()
        self._validate_rating(); self._validate_comments(); self._validate_user(); self._validate_email()
        return not self._errors

    @property
    def errors(self):
        return list(self._errors)

    # ------------------------------------------------------------------ validators
    def _validate_rating(self):
        val = self._require("view", friendly="Rating")
        if val is None: return
        if val not in self._RATING_CHOICES:
            self._errors.append("Invalid rating value."); return
        self.cleaned_data["rating"] = int(val)

    def _validate_comments(self):
        com = self._require("comments", friendly="Comments")
        if com is None: return
        if len(com) > 500:
            self._errors.append("Comments must be 500 characters or fewer."); return
        self.cleaned_data["comments"] = com

    def _validate_user(self):
        uid = self._require("userid", friendly="User ID")
        if uid is None: return
        if not self._USER_RE.fullmatch(uid):
            self._errors.append("User ID must be 4–32 alphanumerics/underscore."); return
        self.cleaned_data["userid"] = uid

    def _validate_email(self):
        em = self._require("email", friendly="Email")
        if em is None: return
        if not self._EMAIL_RE.fullmatch(em):
            self._errors.append("Please enter a valid email address."); return
        self.cleaned_data["email"] = em.lower()

    # ------------------------------------------------------------------ helper
    def _require(self, key: str, *, friendly: str):
        v = self._raw.get(key)
        if v is None or (isinstance(v, str) and not v):
            self._errors.append(f"{friendly} is required.")
            return None
        return v


def validate_feedback_form(data: Dict[str, Any]):
    form = FeedbackForm(data)
    ok = form.is_valid()
    return ok, (form.cleaned_data if ok else form.errors)
