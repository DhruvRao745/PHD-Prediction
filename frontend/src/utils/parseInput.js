// Parses freeform pasted/uploaded data into a {fieldName: value} object
// matching a disease's field config, so a whole row of data can be
// dropped in at once instead of typing every field by hand.
//
// Accepted formats, tried in order:
//   1. JSON object            {"Age": 31, "Glucose": 85, ...}
//   2. "key: value" lines      Age: 31
//                               Glucose: 85
//   3. CSV with header row     Age,Glucose,...
//                               31,85,...
//   4. One row of positional values (comma or whitespace separated),
//      matched to fields in the order they're defined.

export function parseInput(rawText, fields) {
  const text = rawText.trim();
  if (!text) return {};

  try {
    const parsed = JSON.parse(text);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return mapByFieldName(parsed, fields);
    }
  } catch {
    // not JSON, keep trying other formats
  }

  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);

  if (lines.length > 0 && lines.every((l) => /[:=]/.test(l))) {
    const obj = {};
    for (const line of lines) {
      const [key, ...rest] = line.split(/[:=]/);
      obj[key.trim()] = rest.join(":").trim();
    }
    return mapByFieldName(obj, fields);
  }

  if (lines.length >= 2) {
    const header = splitRow(lines[0]);
    const looksLikeHeader = header.some((h) =>
      fields.some((f) => normalize(f.name) === normalize(h))
    );
    if (looksLikeHeader) {
      const values = splitRow(lines[1]);
      const obj = {};
      header.forEach((h, i) => {
        obj[h] = values[i];
      });
      return mapByFieldName(obj, fields);
    }
  }

  const values = splitRow(lines[0] || text);
  const obj = {};
  fields.forEach((f, i) => {
    if (values[i] !== undefined) obj[f.name] = values[i];
  });
  return mapByFieldName(obj, fields);
}

function splitRow(row) {
  const parts = row.includes(",") ? row.split(",") : row.split(/\s+/);
  return parts.map((v) => v.trim()).filter((v) => v !== "");
}

function normalize(s) {
  return String(s).toLowerCase().replace(/[^a-z0-9]/g, "");
}

function mapByFieldName(obj, fields) {
  const result = {};
  const objKeys = Object.keys(obj);

  fields.forEach((field) => {
    const matchKey = objKeys.find((k) => normalize(k) === normalize(field.name));
    if (matchKey === undefined) return;

    let value = obj[matchKey];

    if (field.type === "select") {
      const firstOption = field.options[0];
      value = typeof firstOption === "object" ? Number(value) : String(value).trim().toLowerCase();
    } else {
      // Clamp to the field's min/max so bulk-filled values (which may
      // come straight from a raw dataset row) never trip the number
      // input's native browser validation on submit.
      const num = Number(value);
      if (!Number.isNaN(num)) {
        let clamped = num;
        if (field.min !== undefined) clamped = Math.max(field.min, clamped);
        if (field.max !== undefined) clamped = Math.min(field.max, clamped);
        value = clamped;
      }
    }

    result[field.name] = value;
  });

  return result;
}
