import { rpc } from "./client";

const API = "tecponto_app.tecponto.requests";

export type ApprovalRequest = {
  name: string;
  status: string;
  requested_by: string;
  approver_role: string;
  expires_on: string;
  request_type?: string;
  reason?: string;
  reference_name?: string;
  executed_directly?: boolean;
  execution_result?: Record<string, unknown>;
};

export const approvalRequests = {
  create(requestType: string, referenceName: string, reason: string, payload: Record<string, unknown>) {
    return rpc<ApprovalRequest>(`${API}.create_request`, { body: { request_type: requestType, reference_name: referenceName, reason, payload } });
  },
  mine: () => rpc<ApprovalRequest[]>(`${API}.list_my_requests`),
  pending: () => rpc<ApprovalRequest[]>(`${API}.list_pending_approvals`),
  approve: (name: string) => rpc<ApprovalRequest>(`${API}.approve_request`, { body: { name } }),
  reject: (name: string) => rpc<ApprovalRequest>(`${API}.reject_request`, { body: { name } }),
};
