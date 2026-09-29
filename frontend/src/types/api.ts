export type RiskTier = "Critical" | "High" | "Medium" | "Low" | "Unknown";

export interface AlertSummary {
  alert_id: string;
  account_id: string;
  scenario_id: string;
  scenario_type: "suspicious" | "legitimate" | string;
  risk_score: number;
  risk_tier: RiskTier;
  fired_rules: string[];
  rule_score: number;
  xgb_probability: number;
  iforest_score: number;
  graph_anomaly_score: number;
  is_xgboost_flagged: boolean;
  is_iforest_flagged: boolean;
}

export interface RuleDetail {
  rule_id: string;
  rule_name: string;
  detection_category: string;
  explanation: string;
  evidence_count: number;
}

export interface RuleEngineSignal {
  rule_score: number;
  triggered: boolean;
  fired_rules: string[];
  rule_count: number;
  details: RuleDetail[];
}

export interface ShapFeature {
  feature: string;
  shap_value: number;
  feature_value?: number | string | null;
  impact: "increases_risk" | "decreases_risk" | "neutral" | string;
}

export interface XGBoostSignal {
  probability: number;
  decision_threshold: number;
  is_suspicious: boolean;
  top_shap_features: ShapFeature[];
}

export interface IsolationForestSignal {
  anomaly_score: number;
  threshold: number;
  is_anomaly: boolean;
  interpretation?: string;
  top_contributing_features?: Array<{
    feature: string;
    score_delta?: number;
    value?: number | string;
    baseline_median?: number;
    iqr_deviation?: number;
    direction?: string;
  }>;
}

export interface ClusteringMetrics {
  cluster_label?: number;
  cluster_size?: number;
  is_outlier?: boolean;
}

export interface StructuralMetrics {
  degree?: number;
  in_degree?: number;
  out_degree?: number;
  betweenness_centrality?: number;
  clustering_coefficient?: number;
  is_on_any_cycle?: boolean;
  num_connected_employees?: number;
  [key: string]: unknown;
}

export interface GraphIntelligenceSignal {
  graph_anomaly_score: number;
  contributing_factors: string;
  cycle_membership?: boolean;
  betweenness_quantile?: number;
  structural_metrics: StructuralMetrics;
  clustering_metrics?: ClusteringMetrics;
}

export interface AlertSignals {
  rule_engine: RuleEngineSignal;
  ml_model: {
    xgboost: XGBoostSignal;
    isolation_forest: IsolationForestSignal;
  };
  graph_intelligence: GraphIntelligenceSignal;
}

export interface SubgraphNode {
  id: string;
  type: "Account" | "Customer" | "Employee" | "SyntheticTransaction" | "Transaction" | string;
  label: string;
  raw_id?: string;
  properties?: Record<string, unknown>;
}

export interface SubgraphEdge {
  source: string;
  target: string;
  type: "OWNS" | "MANAGES" | "CHANGED_ACCESS" | "SENT_TO" | "STEP_IN_CYCLE" | string;
  timestamp?: string | null;
  metadata?: Record<string, unknown>;
}

export interface EvidenceSubgraph {
  nodes: SubgraphNode[];
  edges: SubgraphEdge[];
}

export interface TimelineEvent {
  timestamp: string;
  event_type: "access_event" | "transaction" | string;
  category: "scenario_evidence" | "background" | string;
  summary: string;
  details: Record<string, unknown>;
}

export interface AlertDetail {
  alert_id: string;
  account_ids: string[];
  employee_id: string | null;
  risk_tier: RiskTier;
  risk_score: number;
  signals: AlertSignals;
  evidence_subgraph: EvidenceSubgraph;
  timeline: TimelineEvent[];
  explanation: string;
}

export interface EvidencePayload {
  alert_id: string;
  account_id: string;
  risk_tier: RiskTier;
  risk_score: number;
  evidence_subgraph: EvidenceSubgraph;
  timeline: TimelineEvent[];
  explanation: string;
}

export interface CaseRecord {
  case_id: string;
  account_id: string;
  alert_id: string;
  title: string;
  notes: string;
  assigned_to: string;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  status: "OPEN" | "IN_REVIEW" | "CLOSED" | string;
  risk_tier: RiskTier;
  risk_score: number;
  created_at: string;
  updated_at: string;
}

export interface CreateCaseRequest {
  account_id: string;
  alert_id?: string;
  title?: string;
  notes?: string;
  assigned_to?: string;
  priority?: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
}

export interface AssignCaseRequest {
  reviewer: string;
}

export interface ExportCaseResponse {
  export_metadata: {
    exported_at: string;
    system: string;
    version: string;
  };
  case: CaseRecord;
  evidence_package: AlertDetail | Record<string, unknown>;
}
