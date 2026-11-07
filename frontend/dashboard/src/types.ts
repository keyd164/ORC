export interface EditLog { id: number; field_key: string; old_value: string; new_value: string }
export interface Bill {
  [key: string]: unknown;
  id: string; image_id: string; bill_no: string | null; bill_date: string | null;
  room_name: string | null; received_amount: number | null; review_status: string;
  duplicate_status: string; issues_json: string; issues: string[]; edit_logs: EditLog[];
}
export interface ImageRecord { id: string; original_name: string; status: string; business_date: string; error_message: string | null; bill_id: string | null }
export interface OCRRun { id: string; started_at: string; status: string; engine_version: string; raw_text: string; error_message: string | null }
export interface Summary { [key: string]: number | string; received_amount: number; settled: number; pending: number; duplicates: number; total_bills: number; scope: string }
export interface Room { room: string; count: number; received_amount: number; duration_minutes: number }
export interface Trend { date: string; received_amount: number }
export interface Exceptions { bills: Bill[]; images: ImageRecord[] }
export interface AgentSource { kind: 'bill'|'image'|'query'|'document'; id?: string; label: string; url?: string; start?: string; end?: string }
export interface AgentStep { id: number; node: string; tool: string|null; status: string; error_message: string|null; elapsed_ms: number }
export interface AgentRun { id: string; question: string; mode: 'rules'|'ollama'; status: string; answer: string; error_message: string|null; created_at: string; sources: AgentSource[]; steps: AgentStep[] }
