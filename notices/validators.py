from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


MAX_PDF_SIZE = 10 * 1024 * 1024


def validate_pdf_file(uploaded_file):
    if uploaded_file.size > MAX_PDF_SIZE:
        raise ValidationError(_('PDF files must be 10 MB or smaller.'))

    header = uploaded_file.read(5)
    uploaded_file.seek(0)
    if header != b'%PDF-':
        raise ValidationError(_('Upload a valid PDF document.'))
