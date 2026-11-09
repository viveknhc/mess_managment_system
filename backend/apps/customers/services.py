"""Customer business logic — CSV bulk import."""

import csv
import io

from django.db import transaction
from rest_framework import serializers

from apps.customers.models import Customer
from apps.customers.serializers import CustomerCreateSerializer

MAX_IMPORT_ROWS = 100
MAX_IMPORT_BYTES = 1024 * 1024  # 1 MB is plenty for 100 rows

# Canonical columns accepted by the import, in template order.
IMPORT_COLUMNS = ["name", "phone", "email", "address", "location", "notes"]
REQUIRED_COLUMNS = ["name", "phone"]

# Lower-cased header → canonical field name.
HEADER_ALIASES = {
    "name": "name",
    "full name": "name",
    "full_name": "name",
    "customer name": "name",
    "customer_name": "name",
    "phone": "phone",
    "mobile": "phone",
    "mobile number": "phone",
    "mobile_number": "phone",
    "phone number": "phone",
    "phone_number": "phone",
    "contact": "phone",
    "contact number": "phone",
    "whatsapp": "phone",
    "email": "email",
    "email address": "email",
    "e-mail": "email",
    "address": "address",
    "location": "location",
    "area": "location",
    "locality": "location",
    "notes": "notes",
    "note": "notes",
    "remarks": "notes",
}

TEMPLATE_EXAMPLE_ROW = {
    "name": "Ravi Sharma",
    "phone": "9876543210",
    "email": "ravi@example.com",
    "address": "12 MG Road, Pune",
    "location": "MG Road",
    "notes": "Less spicy",
}


class CustomerImportError(serializers.ValidationError):
    """400 VALIDATION_ERROR whose detail is kept verbatim (row numbers stay ints)."""

    def __init__(self, message, fields=None):
        super().__init__()
        detail = {"detail": message}
        if fields:
            detail.update(fields)
        self.detail = detail


def build_import_template() -> str:
    """CSV template: header row + one example row."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=IMPORT_COLUMNS)
    writer.writeheader()
    writer.writerow(TEMPLATE_EXAMPLE_ROW)
    return buf.getvalue()


def parse_customer_csv(raw: bytes) -> list[tuple[int, dict]]:
    """Decode and parse an uploaded CSV into [(row_number, {field: value})].

    Row numbers are 1-based spreadsheet lines (header is row 1). Unknown
    columns (including business_id / customer_code) are ignored. Blank lines
    are skipped.
    """
    if len(raw) > MAX_IMPORT_BYTES:
        raise CustomerImportError("File is too large. Maximum size is 1 MB.")
    try:
        text = raw.decode("utf-8-sig")  # strips BOM if present
    except UnicodeDecodeError as exc:
        raise CustomerImportError("File must be UTF-8 encoded CSV.") from exc

    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise CustomerImportError("The CSV file is empty.") from exc
    except csv.Error as exc:
        raise CustomerImportError(f"Could not parse CSV: {exc}") from exc

    column_map: dict[int, str] = {}
    for idx, col in enumerate(header):
        field = HEADER_ALIASES.get(col.strip().lower())
        if field and field not in column_map.values():
            column_map[idx] = field

    missing = [c for c in REQUIRED_COLUMNS if c not in column_map.values()]
    if missing:
        raise CustomerImportError(
            f"Missing required column(s): {', '.join(missing)}.",
            {"columns": [f"Required columns: {', '.join(REQUIRED_COLUMNS)}."]},
        )

    rows: list[tuple[int, dict]] = []
    try:
        for line in reader:
            if not any(cell.strip() for cell in line):
                continue
            if len(rows) >= MAX_IMPORT_ROWS:
                raise CustomerImportError(
                    f"Too many rows. You can import at most {MAX_IMPORT_ROWS} customers per file."
                )
            data = {
                field: (line[idx].strip() if idx < len(line) else "") for idx, field in column_map.items()
            }
            rows.append((reader.line_num, data))
    except csv.Error as exc:
        raise CustomerImportError(f"Could not parse CSV: {exc}") from exc

    if not rows:
        raise CustomerImportError("The CSV file has no customer rows.")
    return rows


def _check_bulk_quota(business, count: int) -> None:
    """Same rules as TenantScopedViewSet.perform_create's check_quota, for `count` new rows."""
    from apps.platform.middleware import QuotaError, check_quota

    check_quota(business, Customer)  # already at limit → 402
    try:
        plan = business.saas_subscription.plan
    except Exception:
        return
    limit = getattr(plan, "max_customers", 0) if plan else 0
    if not limit:
        return
    current = Customer.objects.filter(business=business).count()
    if current + count > limit:
        raise QuotaError(
            f"Your plan allows a maximum of {limit} customers. "
            f"You have {current}; importing {count} would exceed the limit. Please upgrade your plan."
        )


def import_customers(*, business, raw: bytes, serializer_context: dict) -> int:
    """Validate every CSV row, then create all customers atomically.

    All-or-nothing: if any row fails, nothing is created and a
    CustomerImportError lists `{row, errors}` per failing row.
    Returns the number of customers created.
    """
    rows = parse_customer_csv(raw)

    row_errors = []
    validated = []
    seen_phones: dict[str, int] = {}
    for row_num, data in rows:
        errors = {}
        phone = data.get("phone", "")
        if not phone:
            errors["phone"] = ["Phone is required."]
        elif phone in seen_phones:
            errors["phone"] = [f"Duplicate phone in file (same as row {seen_phones[phone]})."]
        else:
            seen_phones[phone] = row_num

        serializer = CustomerCreateSerializer(data=data, context=serializer_context)
        if not serializer.is_valid():
            for field, msgs in serializer.errors.items():
                errors.setdefault(field, []).extend(str(m) for m in msgs)
        if errors:
            row_errors.append({"row": row_num, "errors": errors})
        else:
            validated.append(serializer)

    if row_errors:
        raise CustomerImportError(
            f"{len(row_errors)} row(s) have errors. No customers were imported.",
            {"rows": row_errors},
        )

    with transaction.atomic():
        _check_bulk_quota(business, len(validated))
        for serializer in validated:
            serializer.save(business_id=business.id)  # CSV business_id never used
    return len(validated)
