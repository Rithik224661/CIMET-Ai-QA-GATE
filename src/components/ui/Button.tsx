import clsx from "clsx";
import type { ButtonHTMLAttributes } from "react";

export type ButtonVariant = "primary" | "secondary";

const BASE = "inline-flex items-center gap-2 rounded-none text-[13px] px-3.5 py-2.5 cursor-pointer disabled:cursor-not-allowed transition-colors";

const VARIANT: Record<ButtonVariant, string> = {
  primary: "bg-text text-cta-ink font-medium border-0 hover:bg-[#e7e7e7] disabled:bg-chip-bg disabled:text-text-dim",
  secondary: "bg-transparent text-text-2 border border-ring hover:border-white/40",
};

/** 0-radius button per CLAUDE.md non-negotiable #2. */
export function buttonClass(variant: ButtonVariant = "secondary", className?: string) {
  return clsx(BASE, VARIANT[variant], className);
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

export default function Button({ variant = "secondary", className, ...props }: ButtonProps) {
  return <button className={buttonClass(variant, className)} {...props} />;
}
