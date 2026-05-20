export type QuoteStatus = "queued" | "ringing" | "talking" | "closed" | "out_of_stock";

export interface DemoRequest {
  request_text: string;
  quantity: number;
  item: string;
  destination: string;
  budget: number;
  needed_by: string;
}

export interface Quote {
  supplier_id: number;
  supplier_name: string;
  location: string;
  language: string;
  status: QuoteStatus;
  price: number | null;
  delivery_hours: number | null;
  reliability: number;
  message: string;
  score: number | null;
}

export interface Decision {
  supplier_id: number;
  supplier_name: string;
  price: number;
  delivery_hours: number;
  reliability: number;
  score: number;
  reason: string;
}

export interface RunSnapshot {
  run_id: string;
  request: DemoRequest;
  status: "running" | "complete";
  quotes: Quote[];
  decision: Decision | null;
}

export interface CheckoutSession {
  transaction_id: string;
  checkout_session_id: string;
  checkout_url: string;
  provider: string;
  mode: string;
  amount: number;
  application_fee_amount: number;
  currency: string;
  status: string;
}

export interface ConversationLine {
  speaker: "agent" | "supplier";
  audioUrl: string;
  text: string;
}
