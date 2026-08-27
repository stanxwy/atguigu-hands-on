export interface AttackPathListItem {
  id: number;
  path_code: string;
  path_title: string;
  path_summary: string | null;
  final_impact_text: string | null;
  vuln_count: number;
  created_at: string;
}

export interface AttackPathStepItem {
  step_order: number;
  step_text: string | null;
  vuln_id: number;
  vuln_code: string | null;
  vuln_title: string | null;
}

export interface AttackPathDetail {
  id: number;
  path_code: string;
  path_title: string;
  path_summary: string | null;
  final_impact_text: string | null;
  items: AttackPathStepItem[];
}
