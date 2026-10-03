export function parseDelimited(input: string, delimiter = ";"): Record<string, string>[] {
  const rows: string[][] = [];
  let row: string[] = [], field = "", quoted = false;
  for (let i = 0; i < input.length; i++) {
    const char = input[i];
    if (char === '"') {
      if (quoted && input[i + 1] === '"') { field += '"'; i++; }
      else quoted = !quoted;
    } else if (!quoted && char === delimiter) { row.push(field.trim()); field = ""; }
    else if (!quoted && (char === "\n" || char === "\r")) {
      if (char === "\r" && input[i + 1] === "\n") i++;
      row.push(field.trim()); if (row.some(Boolean)) rows.push(row);
      row = []; field = "";
    } else field += char;
  }
  if (quoted) throw new Error("Neuzavřené CSV pole.");
  row.push(field.trim()); if (row.some(Boolean)) rows.push(row);
  const header = rows.shift();
  if (!header || new Set(header).size !== header.length) throw new Error("Neplatná CSV hlavička.");
  return rows.map(values => {
    if (values.length !== header.length) throw new Error("CSV neodpovídá hlavičce.");
    return Object.fromEntries(header.map((key, i) => [key.replace(/^\uFEFF/, ""), values[i]]));
  });
}

export function parseScau(input: string) {
  const seen = new Set<string>();
  return input.split(/\r?\n/).filter(line => line.trim()).map(line => {
    const f = line.split("|");
    if (f.length !== 122 || !/^\d{7}$/.test(f[0]) || seen.has(f[0])) throw new Error("Neplatný nebo duplicitní SCAU v21 záznam.");
    seen.add(f[0]);
    const number = (index: number) => {
      const value = f[index].trim().replace(",", ".");
      if (!value) return null;
      if (!/^\d+(?:\.\d+)?$/.test(value)) throw new Error("Neplatná částka SCAU.");
      return Math.round(Number(value) * 100) / 100;
    };
    // v21: UHR1 = column 19; MFC = column 86; OME1 = column 24.
    const m = number(85), a = number(18);
    return { c: f[0], g: null, o: f[23].trim() || null, m, a, s: m !== null && a !== null ? Math.max(0, Math.round((m - a) * 100) / 100) : null };
  });
}
