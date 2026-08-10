from django import template
from decimal import Decimal

register = template.Library()


@register.filter(is_safe=True)
def euro(value, decimals=2):
    """Format a number using European style: point for thousands, comma for decimals.

    Examples:
        2561.1 -> '2.561,10'
        52.3 -> '52,30'
    """
    if value is None:
        return ''

    try:
        # Allow strings with comma as decimal separator
        if isinstance(value, str):
            value = value.replace(',', '.')
            num = Decimal(value)
        elif isinstance(value, Decimal):
            num = value
        else:
            # int/float
            num = Decimal(str(value))

        # Format with thousands separator (','), decimal point ('.') then swap
        s = format(num, f",.{int(decimals)}f")
        # Convert '2,561.10' -> '2.561,10'
        s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
        return s
    except Exception:
        # Fallback: return original value
        return value
