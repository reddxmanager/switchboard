import type {
  CheckoutSession,
  DemoRequest,
  RunSnapshot,
} from "./types";

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export const WS_BASE = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";

export const demoRequest: DemoRequest = {
  request_text: "I need 20 bags of cement delivered to Zambales by Friday, budget 8,000.",
  quantity: 20,
  item: "cement bags",
  destination: "Zambales",
  budget: 8000,
  needed_by: "Friday",
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function startNegotiation(): Promise<RunSnapshot> {
  return request<RunSnapshot>("/negotiations", {
    method: "POST",
    body: JSON.stringify(demoRequest),
  });
}

export function createCheckout(runId: string): Promise<CheckoutSession> {
  return request<CheckoutSession>("/checkout", {
    method: "POST",
    body: JSON.stringify({ run_id: runId }),
  });
}
