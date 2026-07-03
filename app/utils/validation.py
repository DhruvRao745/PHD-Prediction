def check_missing_fields(data, required_fields):
    missing = [f for f in required_fields if f not in data]
    if missing:
        return f"Missing required fields: {', '.join(missing)}"
    return None


def check_numeric_fields(data, required_fields):
    for field in required_fields:
        if not isinstance(data[field], (int, float)):
            return f"Field '{field}' must be a number"
    return None

def validate_numeric(data, field_ranges):
    """
    Validate numeric fields with required ranges.

    data: dict of input values
    field_ranges: { field_name: (min, max) }
    """

    errors = []

    for field, (min_val, max_val) in field_ranges.items():

        # Check missing
        if field not in data:
            errors.append(f"{field} is missing")
            continue

        value = data[field]

        # Check type
        if not isinstance(value, (int, float)):
            errors.append(f"{field} must be a number")
            continue

        # Check range
        if value < min_val or value > max_val:
            errors.append(
                f"{field} must be between {min_val} and {max_val}"
            )

    return errors

def validate_schema(data, schema):
    errors = []

    for field, (min_val, max_val) in schema.items():

        if field not in data:
            errors.append(f"{field} is missing")
            continue

        value = data[field]

        if not isinstance(value, (int, float)):
            errors.append(f"{field} must be a number")
            continue

        if value < min_val or value > max_val:
            errors.append(
                f"{field} must be between {min_val} and {max_val}"
            )

    return errors


def validate_kidney_schema(
    data,
    numeric_schema,
    categorical_schema,
):
    errors = []

    # Validate numeric fields
    for field, (min_val, max_val) in numeric_schema.items():

        if field not in data:
            errors.append(f"{field} is missing")
            continue

        value = data[field]

        if not isinstance(value, (int, float)):
            errors.append(f"{field} must be a number")
            continue

        if value < min_val or value > max_val:
            errors.append(
                f"{field} must be between "
                f"{min_val} and {max_val}"
            )

    # Validate categorical fields
    for field, allowed_values in categorical_schema.items():

        if field not in data:
            errors.append(f"{field} is missing")
            continue

        value = data[field]

        if not isinstance(value, str):
            errors.append(f"{field} must be text")
            continue

        cleaned_value = value.strip().lower()

        if cleaned_value not in allowed_values:
            errors.append(
                f"{field} must be one of: "
                f"{', '.join(allowed_values)}"
            )

    return errors