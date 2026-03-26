function parseDateValue(value: string) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return new Date(`${value}T00:00:00`);
  }

  return new Date(value);
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "Not set";
  }

  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parseDateValue(value));
}

export function formatDate(value: string | null | undefined) {
  if (!value) {
    return "Not set";
  }

  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
  }).format(parseDateValue(value));
}

export function formatStatusLabel(value: string, explicitLabel?: string | null) {
  if (explicitLabel?.trim()) {
    return explicitLabel;
  }

  return value.replace(/[_-]/g, " ");
}

export function formatActionLabel(value: string) {
  return value.replace(/[._]/g, " ");
}
