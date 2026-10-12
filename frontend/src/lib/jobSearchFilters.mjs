const stateCodes = new Set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split(" "));

export function jobSearchFilters(workplace, location) {
  if (workplace === "remote") return { country: "US", workplace, location: "" };
  if (workplace !== "local") throw new Error("Choose Remote or Hybrid / in-person.");
  if (!location.trim()) return { country: "US", workplace, location: "" };
  const match = /^([\p{L}][\p{L}\p{M} .'-]*),\s*([A-Za-z]{2})$/u.exec(location.trim());
  if (!match || !stateCodes.has(match[2].toUpperCase())) {
    throw new Error("Enter a city and valid state abbreviation, such as Boston, MA.");
  }
  return { country: "US", workplace, location: `${match[1].trim()}, ${match[2].toUpperCase()}` };
}
