export type Confidence = "high" | "medium" | "low";
export const UNSUPPORTED = "UNSUPPORTED" as const;

export interface Citation {
  chunk_id: string;
  quote: string;
}

export interface Fact {
  sentence_id: string;
  text: string;
  citations: Citation[];
  confidence: Confidence;
}

export interface CaseFactSummary {
  parties: Fact[];
  jurisdiction: Fact[];
  key_dates: Fact[];
  claims: Fact[];
  relief_sought: Fact[];
  procedural_posture: Fact[];
  key_evidence: Fact[];
}

export const SLOT_ORDER: (keyof CaseFactSummary)[] = [
  "parties",
  "jurisdiction",
  "key_dates",
  "claims",
  "relief_sought",
  "procedural_posture",
  "key_evidence",
];
