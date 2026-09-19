import { redirect } from "next/navigation";
import { DEFAULT_LEAD_ID } from "@/lib/fixtures/leads";

export default function SalesIndexPage() {
  redirect(`/sales/${DEFAULT_LEAD_ID}`);
}
