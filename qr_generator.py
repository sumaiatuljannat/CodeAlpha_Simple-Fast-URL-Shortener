"""
QR code generation utility using Segno.
Supports vector SVG and high-resolution data URI output with zero heavy binary dependencies.
"""
import io
import segno


def generate_qr_svg(url: str, scale: int = 8) -> str:
    """
    Generates a crisp SVG string for the given URL.
    """
    qr = segno.make(url, error='m')
    out = io.BytesIO()
    qr.save(out, kind='svg', scale=scale, dark='#0f172a', light='#ffffff', border=2)
    return out.getvalue().decode('utf-8')


def generate_qr_data_uri(url: str, scale: int = 6) -> str:
    """
    Generates an inline SVG data URI suitable for direct usage in HTML <img src="..."> tags.
    """
    qr = segno.make(url, error='m')
    return qr.svg_data_uri(scale=scale, dark='#0f172a', light='#ffffff', border=2)


def generate_qr_png_bytes(url: str, scale: int = 10) -> bytes:
    """
    Generates high-resolution PNG bytes for download.
    Segno supports pure Python PNG writing without requiring C-compiled Pillow.
    """
    qr = segno.make(url, error='m')
    out = io.BytesIO()
    qr.save(out, kind='png', scale=scale, dark='#0f172a', light='#ffffff', border=2)
    return out.getvalue()
