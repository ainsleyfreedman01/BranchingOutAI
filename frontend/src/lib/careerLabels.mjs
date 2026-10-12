export function canonicalizeCareerLabel(label) {
  return label.replace(/\b(ai|ml|ux|ui|nlp|api)\b/gi, (acronym) => acronym.toUpperCase());
}
