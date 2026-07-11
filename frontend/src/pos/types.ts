import type { PosItemSummary } from "../api";

export interface PosCartLine extends PosItemSummary {
  qty: number;
}

export type PosSearchStatus = "idle" | "loading" | "ready" | "error";
export type PosScanStatus = "idle" | "loading" | "success" | "error";

export interface PosScanFeedback {
  detail: string;
  title: string;
}

export type PosToast = (message: string, tone?: "success" | "error") => void;

export const brl = new Intl.NumberFormat("pt-BR", {
  currency: "BRL",
  style: "currency",
});
