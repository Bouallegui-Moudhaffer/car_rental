import re
from typing import Any, Dict, List, Tuple


# ---------------------------------------------------------------------------
# Validators for the three payment flows
# ---------------------------------------------------------------------------

class _Base:
    """Shared helper base."""

    def __init__(self, raw: Dict[str, Any]):
        self._raw = {k: (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}
        self.cleaned_data: Dict[str, Any] = {}
        self._errors: List[str] = []

    def _require(self, key: str, *, friendly: str):
        v = self._raw.get(key)
        if v is None or (isinstance(v, str) and not v):
            self._errors.append(f"{friendly} is required.")
            return None
        return v

    def is_valid(self) -> bool:
        raise NotImplementedError

    @property
    def errors(self) -> List[str]:
        return list(self._errors)


# ---------------------------------------------------------------------------
# Credit / Debit card form
# ---------------------------------------------------------------------------

class CardPaymentForm(_Base):
    _NAME_RE = re.compile(r"^[A-Za-z ]{2,50}$")
    _CARD_RE = re.compile(r"^(?:\d{4}-){3}\d{4}$|^\d{16}$")

    def is_valid(self) -> bool:
        self._errors.clear(); self.cleaned_data.clear()
        name = self._require("name", friendly="Name on card");
        if name and not self._NAME_RE.fullmatch(name):
            self._errors.append("Name must be 2–50 letters/spaces.")
        else:
            self.cleaned_data["name"] = name

        num = self._require("cardnumber", friendly="Card number")
        if num and not self._CARD_RE.fullmatch(num):
            self._errors.append("Card number must be 16 digits (with or without dashes).")
        else:
            self.cleaned_data["cardnumber"] = (num.replace("-", "") if num else None)

        return not self._errors


# ---------------------------------------------------------------------------
# Netbanking form
# ---------------------------------------------------------------------------

class NetbankingForm(_Base):
    _RADIO_CHOICES = {"0", "1"}  # 0 = Paid, 1 = Not Paid

    def is_valid(self) -> bool:
        self._errors.clear(); self.cleaned_data.clear()
        val = self._require("radio", friendly="Payment status")
        if val and val not in self._RADIO_CHOICES:
            self._errors.append("Invalid payment-status selection.")
        else:
            self.cleaned_data["radio"] = val or "1"  # default Not Paid if missing
        return not self._errors


# Convenience wrappers -------------------------------------------------------

def validate_card_form(data: Dict[str, Any]):
    form = CardPaymentForm(data)
    ok = form.is_valid()
    return ok, (form.cleaned_data if ok else form.errors)


def validate_netbanking_form(data: Dict[str, Any]):
    form = NetbankingForm(data)
    ok = form.is_valid()
    return ok, (form.cleaned_data if ok else form.errors)
