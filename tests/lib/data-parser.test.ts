import { describe, it, expect } from "vitest";
import { parseDelimited, parseScau } from "../../scripts/data-parser";
describe("Official data parsers", () => {
  it("handles quoted delimiters, escaped quotes, newlines and CRLF", () => {
    expect(parseDelimited('CODE;NAME\r\n1;"A;B\nC ""D"""\r\n')).toEqual([{CODE:"1",NAME:'A;B\nC "D"'}]);
    expect(() => parseDelimited('A;B\n1')).toThrow();
    expect(() => parseDelimited('A;B\n1;"unfinished')).toThrow();
  });
  it("maps independent SCAU v21 reference amounts, keeping prescriber restriction separate", () => {
    const row = Array(122).fill(""); row[0]="0094156"; row[18]="79,76"; row[19]="51,98"; row[23]="ATB"; row[85]="162,82";
    expect(parseScau(row.join("|"))).toEqual([{c:"0094156",g:null,o:"ATB",m:162.82,a:79.76,s:83.06}]);
    expect(() => parseScau(row.slice(0,121).join("|"))).toThrow();
    expect(() => parseScau(`${row.join("|")}\n${row.join("|")}`)).toThrow();
    row[85]="12 garbage"; expect(() => parseScau(row.join("|"))).toThrow();
  });
});
