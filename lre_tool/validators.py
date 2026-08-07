"""Input validators shared by the PyQt interface."""

from PyQt5.QtGui import QDoubleValidator


class FlexibleDoubleValidator(QDoubleValidator):
    """Accept both a decimal point and a decimal comma for the active locale."""

    def validate(self, text, position):
        decimal_point = self.locale().decimalPoint()
        alternate = "," if decimal_point == "." else "."
        normalized = text.replace(alternate, decimal_point)
        state, _, _ = super().validate(normalized, position)
        return state, text, position
