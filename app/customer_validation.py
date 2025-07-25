import re
from typing import Dict, List, Any


class ValidationError(Exception):
    """Raised when the form data fails validation."""

    def __init__(self, errors: List[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


class RegistrationForm:
    """Server-side validation for *addcustomer.html*.

    Usage
    -----
    >>> form = RegistrationForm(request.form)
    >>> if form.is_valid():
    ...     cleaned = form.cleaned_data  # safely-typed / normalised values
    ... else:
    ...     flash(" ".join(form.errors))
    ...
    """

    _NAME_RE = re.compile(r"^[A-Za-z]+$")
    _USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,32}$")
    _EMAIL_RE = re.compile(r"^[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9-.]+$")
    _PHONE_RE = re.compile(r"^[0-9]{10}$")
    _PASSWORD_POLICY_RE = re.compile(
        r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()\-_=+{};:,<.>]).{8,64}$"
    )

    #: Allowed security-question numeric choices as strings
    _SQUESTION_CHOICES = {"1", "2", "3", "4"}  # "0" == Select Security Question (invalid)

    def __init__(self, raw_data: Dict[str, Any]):
        # convert ImmutableMultiDict or dict-like to plain dict[str,str]
        self._raw = {k: (v.strip() if isinstance(v, str) else v) for k, v in raw_data.items()}
        self.cleaned_data: Dict[str, Any] = {}
        self._errors: List[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def is_valid(self) -> bool:
        """Run all validators; populate *cleaned_data* and *errors*."""
        self._errors.clear()
        self.cleaned_data.clear()

        self._validate_name("FName", friendly="First name")
        self._validate_name("lName", friendly="Last name")
        self._validate_username()
        self._validate_email()
        self._validate_phone()
        self._validate_age()
        self._validate_passwords()
        self._validate_security()
        self._validate_answer()

        return not self._errors

    @property
    def errors(self) -> List[str]:
        return list(self._errors)

    # ------------------------------------------------------------------
    # Field-level validators
    # ------------------------------------------------------------------
    def _validate_name(self, key: str, *, friendly: str) -> None:
        value = self._require(key, friendly=friendly)
        if value is None:
            return
        if not self._NAME_RE.match(value):
            self._errors.append(f"{friendly} must contain letters only (A-Z).")
            return
        self.cleaned_data[key] = value.capitalize()

    def _validate_username(self) -> None:
        value = self._require("username", friendly="Username")
        if value is None:
            return
        if not self._USERNAME_RE.match(value):
            self._errors.append(
                "Username must be 4-32 characters of letters, numbers, or underscores."
            )
            return
        self.cleaned_data["username"] = value

    def _validate_email(self) -> None:
        value = self._require("email", friendly="Email")
        if value is None:
            return
        if not self._EMAIL_RE.match(value):
            self._errors.append("Please enter a valid email address.")
            return
        self.cleaned_data["email"] = value.lower()

    def _validate_phone(self) -> None:
        value = self._require("PhoneNumber", friendly="Phone number")
        if value is None:
            return
        if not self._PHONE_RE.match(value):
            self._errors.append("Phone number must be exactly 10 digits.")
            return
        self.cleaned_data["phone"] = value

    def _validate_age(self) -> None:
        value = self._require("age", friendly="Age")
        if value is None:
            return
        try:
            age_int = int(value)
        except ValueError:
            self._errors.append("Age must be a number.")
            return
        if age_int < 15:
            self._errors.append("You must be at least 15 years old to register.")
            return
        if age_int > 120:
            self._errors.append("Age seems unrealistic; please enter a valid age.")
            return
        self.cleaned_data["age"] = age_int

    def _validate_passwords(self) -> None:
        pwd = self._require("Password", friendly="Password")
        conf = self._require("ConfirmPassword", friendly="Confirm password")
        if None in (pwd, conf):
            return

        if pwd != conf:
            self._errors.append("Password and confirmation do not match.")
            return

        if not self._PASSWORD_POLICY_RE.match(pwd):
            self._errors.append(
                (
                    "Password must be 8-64 characters and include upper & lower-case letters, "
                    "a digit, and a special character."
                )
            )
            return
        self.cleaned_data["password"] = pwd

    def _validate_security(self) -> None:
        choice = self._require("squestion", friendly="Security question")
        if choice is None:
            return
        if choice not in self._SQUESTION_CHOICES:
            self._errors.append("Please select a valid security question.")
            return
        self.cleaned_data["squestion"] = int(choice)

    def _validate_answer(self) -> None:
        ans = self._require("answer", friendly="Security answer")
        if ans is None:
            return
        if len(ans) > 64:
            self._errors.append("Security answer must be 64 characters or fewer.")
            return
        self.cleaned_data["answer"] = ans

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _require(self, key: str, *, friendly: str):
        value = self._raw.get(key)
        if value is None or (isinstance(value, str) and not value):
            self._errors.append(f"{friendly} is required.")
            return None
        return value


# ----------------------------------------------------------------------
# Convenience function if you prefer functional style over classes
# ----------------------------------------------------------------------

def validate_registration_form(form_data: Dict[str, Any]):
    """Validate *addcustomer.html* POST data.

    Returns (is_ok, cleaned_or_errors):
      * is_ok == True  -> cleaned_or_errors = cleaned_data (dict)
      * is_ok == False -> cleaned_or_errors = list[str] of errors
    """
    form = RegistrationForm(form_data)
    ok = form.is_valid()
    return (ok, form.cleaned_data if ok else form.errors)
