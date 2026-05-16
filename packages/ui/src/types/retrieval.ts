export interface ChunkMeta {
  chunk_id: string;
  doc_id: string;
  doc_title?: string;
  page: number;
  section_label: string | null;
  char_start: number;
  char_end: number;
  text: string;
  contains_needs_review: boolean;
}
